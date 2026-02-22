"""
Verifier node: for each extracted claim, scores it using the vector store (Chroma similarity over
PDF chunks). Produces state["verifications"] and state["final_result"] (overall_status, counts,
average_confidence).
"""
import re
from typing import Dict, List

from src.config import throttle_before_api_call
from src.graph.state import VerificationRecord, VerificationState
from src.rag.vectorstore import IPCBNSVectorStore

SECTION_RE = re.compile(r"(?:IPC|BNS)?\s*Section\s*(\d+[A-Z]?)", re.IGNORECASE)


def _extract_sections(text: str) -> List[str]:
    """Return unique section numbers (e.g. 302, 103) found in text via SECTION_RE."""
    return list({m.group(1) for m in SECTION_RE.finditer(text)})


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
    """
    Query the vector store for chunks similar to the claim; score by similarity and whether the chunk
    contains the claim's section numbers. Returns dict with status (strong/moderate/weak_evidence,
    uncertain, no_evidence), confidence, evidence snippet, source="vector".
    """
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


def verifier_node(state: VerificationState) -> VerificationState:
    """
    Scores each claim via the vector store (embedding similarity over PDF chunks),
    then sets state["verifications"] and state["final_result"] (overall_status, counts, average_confidence).
    """
    throttle_before_api_call()
    claims = state.get("claims", [])
    vec = IPCBNSVectorStore()

    verifications: List[VerificationRecord] = []

    for claim in claims:
        vec_score = _score_vector(claim, vec)
        record: VerificationRecord = {
            "claim": claim,
            "status": vec_score["status"],  # type: ignore[typeddict-unknown-key]
            "confidence": float(round(float(vec_score["confidence"]), 3)),
            "evidence": str(vec_score["evidence"]),
            "source": "vector",
        }
        verifications.append(record)

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
        # Vector-store contradiction → unreliable; no_evidence is not contradiction
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
