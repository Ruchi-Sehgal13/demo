"""
Shared state for the verification workflow. All nodes read from and write to VerificationState;
VerificationRecord describes one verified claim (status, confidence, evidence).
"""
from typing import Any, Dict, List, Literal, TypedDict

# Tiered by strength of evidence (vector similarity + optional section match)
StatusLabel = Literal[
    "strong_evidence",    # high similarity, chunk clearly supports
    "moderate_evidence",  # decent match
    "weak_evidence",      # some relevance, not enough to fully trust
    "uncertain",          # cannot tell
    "no_evidence",        # no relevant evidence in KB — model's claim, not verified
    "contradicted",       # Vector store / KB explicitly contradicts
]


class VerificationRecord(TypedDict):
    """One claim plus its verification result: status, confidence, evidence snippet, and source (vector)."""
    claim: str
    status: StatusLabel
    confidence: float
    evidence: str
    source: str  # "vector"


class VerificationState(TypedDict, total=False):
    """
    State passed through the LangGraph workflow. All keys are optional (total=False).
    Nodes read existing keys and add/update others as the pipeline runs.
    """
    # Input
    question: str
    llm_provider: str
    llm_model: str

    # Primary LLM output
    llm_answer: str

    # Claims
    claims: List[str]

    # Verification
    verifications: List[VerificationRecord]
    final_result: Dict[str, Any]

    # Evaluation
    evaluation: Dict[str, Any]

    # Misc
    metadata: Dict[str, Any]
