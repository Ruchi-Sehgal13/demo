"""
Verifier node: for each claim, (1) retrieves relevant KB chunks via semantic search,
(2) calls an LLM to decide if the retrieved content supports the claim. Output is verified true/false
per claim (no confidence). Produces state["verifications"] and state["final_result"].
"""
import re
from typing import List, Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from src.config import LLMConfig, get_llm, throttle_before_api_call
from src.graph.state import VerificationRecord, VerificationState
from src.rag.vectorstore import IPCBNSVectorStore

SECTION_RE = re.compile(r"(?:IPC|BNS)?\s*Section\s*(\d+[A-Z]?)", re.IGNORECASE)

# How many chars of retrieved text to send to the LLM (avoid token limits)
EVIDENCE_MAX_CHARS = 2000

VERIFY_SYSTEM = """You are a fact-checker. Your task is to determine whether a KNOWLEDGE BASE EXCERPT supports a given CLAIM.

Rules:
- The excerpt is from a trusted IPC–BNS legal knowledge base.
- If the excerpt clearly supports or confirms the claim, answer TRUE.
- If the excerpt is irrelevant, does not mention the claim, or contradicts the claim, answer FALSE.
- Answer only TRUE or FALSE. No explanation."""

VERIFY_USER = """CLAIM:
{claim}

KNOWLEDGE BASE EXCERPT:
{evidence}

Does the excerpt support the claim? Answer TRUE or FALSE."""


def _extract_sections(text: str) -> List[str]:
    """Return unique section numbers (e.g. 302, 103) found in text."""
    return list({m.group(1) for m in SECTION_RE.finditer(text)})


def _retrieve_evidence(claim: str, vec: IPCBNSVectorStore, k: int = 5) -> str:
    """
    Semantic search: get top-k chunks for the claim and return their text concatenated.
    Used as evidence for the LLM verification step.
    """
    secs = _extract_sections(claim)
    query = (
        f"{claim} IPC BNS section conversion mapping {' '.join(secs)}".strip()
        if secs
        else claim
    )
    results = vec.query(query, k=k)
    if not results:
        return ""
    texts = [r[0] for r in results]
    combined = "\n\n---\n\n".join(texts)
    return combined[:EVIDENCE_MAX_CHARS]


class VerificationOutput(BaseModel):
    """Structured LLM output: does the knowledge base excerpt support the claim?
    Uses literal strings so providers (e.g. Groq) that serialize as 'TRUE'/'FALSE' pass validation."""
    verified: Literal["TRUE", "FALSE"]


def _llm_verify(claim: str, evidence: str, state: VerificationState) -> bool:
    """Call LLM with claim + evidence; return True if excerpt supports claim, else False."""
    if not evidence.strip():
        return False
    throttle_before_api_call()
    provider = state.get("llm_provider", "groq")
    model = state.get("llm_model") or "llama-3.3-70b-versatile"
    llm = get_llm(LLMConfig(provider=provider, model=model))
    prompt = ChatPromptTemplate.from_messages(
        [("system", VERIFY_SYSTEM), ("user", VERIFY_USER)]
    )
    chain = prompt | llm.with_structured_output(VerificationOutput)
    result = chain.invoke({"claim": claim, "evidence": evidence})
    return result.verified == "TRUE"


def verifier_node(state: VerificationState) -> VerificationState:
    """
    For each claim: retrieve evidence from vector store, then LLM verifies whether the evidence
    supports the claim. Sets state["verifications"] (verified true/false per claim) and
    state["final_result"] (verified_claims, not_verified_claims, total_claims, overall_status).
    """
    claims = state.get("claims", [])
    vec = IPCBNSVectorStore()

    verifications: List[VerificationRecord] = []

    for claim in claims:
        evidence = _retrieve_evidence(claim, vec)
        if not evidence.strip():
            verified = False
            evidence = "(No relevant chunks found in knowledge base.)"
        else:
            verified = _llm_verify(claim, evidence, state)
        record: VerificationRecord = {
            "claim": claim,
            "verified": verified,
            "evidence": evidence,
            "source": "vector",
        }
        verifications.append(record)

    state["verifications"] = verifications

    verified_count = sum(1 for v in verifications if v["verified"])
    not_verified_count = len(verifications) - verified_count
    total = len(verifications)

    if total == 0:
        overall = "no_claims"
    elif verified_count == total:
        overall = "reliable"
    elif not_verified_count == total:
        overall = "unreliable"
    else:
        overall = "uncertain"

    state["final_result"] = {
        "overall_status": overall,
        "verified_claims": verified_count,
        "not_verified_claims": not_verified_count,
        "total_claims": total,
    }
    return state
