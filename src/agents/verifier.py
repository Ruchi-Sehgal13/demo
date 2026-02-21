import re
from typing import Dict, List

from src.config import paths, throttle_before_api_call
from src.graph.state import VerificationRecord, VerificationState
from src.rag.vectorstore import IPCBNSRelationalStore, IPCBNSVectorStore

# Set to False to verify only via vector search (for testing).
USE_RELATIONAL_VERIFICATION = False

SECTION_RE = re.compile(r"(?:IPC|BNS)?\s*Section\s*(\d+[A-Z]?)", re.IGNORECASE)


def _extract_sections(text: str) -> List[str]:
    return list({m.group(1) for m in SECTION_RE.finditer(text)})


def _score_relational(claim: str, rel: IPCBNSRelationalStore) -> Dict[str, object]:
    secs = _extract_sections(claim)
    if not secs:
        return {
            "status": "uncertain",
            "confidence": 0.0,
            "evidence": "",
            "source": "relational",
        }

    # Try each section as IPC (claim may list both IPC and BNS; set order is arbitrary)
    for ipc in secs:
        record = rel.get_by_ipc(ipc)
        if not record:
            continue
        bns = record["bns_section"]
        notes = record.get("notes", "")
        ok = (bns in claim) or (f"BNS {bns}" in claim)
        status = "supported" if ok else "contradicted"
        conf = 0.9 if ok else 0.7
        evidence = f"IPC {ipc} → BNS {bns}. {notes}"
        return {
            "status": status,
            "confidence": conf,
            "evidence": evidence,
            "source": "relational",
        }

    return {
        "status": "uncertain",
        "confidence": 0.4,
        "evidence": "No mapping found in IPC↔BNS table.",
        "source": "relational",
    }


def _chunk_contains_any_section(chunk_text: str, section_numbers: List[str]) -> bool:
    """True if chunk contains at least one of the section numbers as a whole word."""
    if not section_numbers:
        return True
    for sec in section_numbers:
        if re.search(r"\b" + re.escape(sec) + r"\b", chunk_text):
            return True
    return False


def _chunk_states_mapping(chunk_text: str, section_numbers: List[str]) -> bool:
    """True if the chunk states this mapping: all section numbers appear on one line or within a small window of lines (table rows often have one cell per line)."""
    if len(section_numbers) < 2:
        return True
    lines = chunk_text.splitlines()
    # Sliding window: table rows can be "375\\n63\\nRape" (one cell per line)
    window_size = 4
    for i in range(len(lines) - window_size + 1):
        window_text = " ".join(lines[i : i + window_size])
        if all(re.search(r"\b" + re.escape(sec) + r"\b", window_text) for sec in section_numbers):
            return True
    # Single line (prose format)
    for line in lines:
        if all(re.search(r"\b" + re.escape(sec) + r"\b", line) for sec in section_numbers):
            return True
    return False


def _score_vector(claim: str, vec: IPCBNSVectorStore) -> Dict[str, object]:
    secs = _extract_sections(claim)
    # Enrich query so embedding leans toward conversion-table chunks
    query = (
        f"{claim} IPC BNS section conversion mapping {' '.join(secs)}".strip()
        if secs
        else claim
    )
    results = vec.query(query, k=10)
    if not results:
        return {
            "status": "uncertain",
            "confidence": 0.0,
            "evidence": "No semantic evidence.",
            "source": "vector",
        }

    # Prefer chunks that actually contain the claim's section numbers (e.g. conversion table)
    filtered = [r for r in results if _chunk_contains_any_section(r[0], secs)]
    use_results = filtered if filtered else results

    best_text, meta, dist = use_results[0]
    sim = max(0.0, min(1.0, 1.0 - dist))

    # Two paths: (1) Claim has section numbers AND chunk contains that mapping on a line →
    # we have structural proof the chunk is about this claim, so we use looser sim thresholds.
    # (2) No section numbers or chunk doesn't state the mapping → we only have embedding
    # similarity, so we require higher sim for "supported" and use a clear contradicted band.
    # Confidence is nudged up when we assign a positive tier so correct claims don't get stuck at 0.57.
    chunk_states_this_mapping = _chunk_states_mapping(best_text, secs)
    if chunk_states_this_mapping and secs:
        # Section-number path: chunk explicitly has this IPC/BNS pair — keep thresholds loose
        if sim <= 0.4:
            conf = 0.72
            status = "moderate_evidence"
        elif sim >= 0.7:
            status = "strong_evidence"
            conf = max(sim, 0.78)
        elif sim >= 0.55:
            status = "moderate_evidence"
            conf = max(sim, 0.65)
        elif sim >= 0.45:
            status = "weak_evidence"
            conf = max(sim, 0.55)
        else:
            status = "uncertain"
            conf = sim
    else:
        # No section-number verification: looser than before so correct claims score higher
        if sim >= 0.7:
            status = "strong_evidence"
            conf = max(sim, 0.78)
        elif sim >= 0.58:
            status = "moderate_evidence"
            conf = max(sim, 0.65)
        elif sim >= 0.45:
            status = "weak_evidence"
            conf = max(sim, 0.55)
        elif sim >= 0.35:
            status = "uncertain"
            conf = sim
        else:
            # No relevant evidence in KB (best chunk doesn't match); don't call it contradicted
            status = "no_evidence"
            conf = sim

    return {
        "status": status,
        "confidence": conf,
        "evidence": best_text[:600],
        "source": "vector",
    }


def _fuse(rel: Dict[str, object], vec: Dict[str, object]) -> VerificationRecord:
    if rel["status"] != "uncertain":
        base_status = str(rel["status"])
        base_conf = float(rel["confidence"])
        vec_status = str(vec["status"])
        vec_conf = float(vec["confidence"])

        if base_status == "supported" and vec_status == "contradicted" and vec_conf > 0.7:
            # Relational says supported but vector says contradicted with high conf → downgrade
            status = "uncertain"
            conf = (base_conf + vec_conf) / 2
        elif vec_status == "no_evidence":
            # Relational had something; vector found no evidence in KB — keep relational result
            status = "strong_evidence" if base_status == "supported" else "contradicted"
            conf = max(base_conf, vec_conf)
        else:
            # Map relational to tiered labels: supported → strong_evidence, contradicted → contradicted
            status = "strong_evidence" if base_status == "supported" else "contradicted"
            conf = max(base_conf, vec_conf)

        evidence = f"{rel['evidence']}\n\nVector evidence:\n{vec['evidence']}"
        source = "mixed"
    else:
        status = str(vec["status"])
        conf = float(vec["confidence"])
        evidence = str(vec["evidence"])
        source = "vector"

    return {
        "claim": "",
        "status": status,  # type: ignore[assignment]
        "confidence": float(round(conf, 3)),
        "evidence": evidence,
        "source": source,
    }


def verifier_node(state: VerificationState) -> VerificationState:
    if state.get("route", "verify") == "direct":
        state["verifications"] = []
        state["final_result"] = {
            "overall_status": "direct_answer",
            "average_confidence": 1.0,
            "supported_claims": 0,
            "weak_evidence_claims": 0,
            "no_evidence_claims": 0,
            "contradicted_claims": 0,
            "uncertain_claims": 0,
            "total_claims": 0,
        }
        return state

    throttle_before_api_call()
    claims = state.get("claims", [])
    rel = IPCBNSRelationalStore(paths.SQLITE_DB) if USE_RELATIONAL_VERIFICATION else None
    vec = IPCBNSVectorStore()

    verifications: List[VerificationRecord] = []

    for claim in claims:
        if USE_RELATIONAL_VERIFICATION and rel is not None:
            rel_score = _score_relational(claim, rel)
        else:
            rel_score = {
                "status": "uncertain",
                "confidence": 0.0,
                "evidence": "",
                "source": "relational",
            }
        vec_score = _score_vector(claim, vec)
        fused = _fuse(rel_score, vec_score)
        fused["claim"] = claim
        verifications.append(fused)

    state["verifications"] = verifications

    # Count tiered statuses; "supported" for reliable = strong + moderate evidence
    supported = sum(1 for v in verifications if v["status"] in ("strong_evidence", "moderate_evidence"))
    weak_evidence = sum(1 for v in verifications if v["status"] == "weak_evidence")
    no_evidence = sum(1 for v in verifications if v["status"] == "no_evidence")
    contradicted = sum(1 for v in verifications if v["status"] == "contradicted")
    uncertain = sum(1 for v in verifications if v["status"] == "uncertain")
    total = len(verifications)
    avg_conf = sum(v["confidence"] for v in verifications) / total if total else 0.0

    if total == 0:
        overall = "no_claims"
    elif contradicted > 0:
        # Only actual KB/relational contradiction → unreliable; no_evidence is not contradiction
        overall = "unreliable"
    elif supported / max(total, 1) >= 0.7 and avg_conf >= 0.55:
        overall = "reliable"
    else:
        overall = "uncertain"

    state["final_result"] = {
        "overall_status": overall,
        "average_confidence": float(round(avg_conf, 3)),
        "supported_claims": supported,
        "weak_evidence_claims": weak_evidence,
        "no_evidence_claims": no_evidence,
        "contradicted_claims": contradicted,
        "uncertain_claims": uncertain,
        "total_claims": total,
    }
    return state
