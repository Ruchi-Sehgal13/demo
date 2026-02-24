"""
Shared state for the verification workflow. All nodes read from and write to VerificationState;
VerificationRecord describes one claim and whether it was verified (true/false) against the KB.
"""
from typing import Any, Dict, List, TypedDict


class VerificationRecord(TypedDict):
    """One claim plus verification result: verified (true/false), evidence snippet from KB, source."""
    claim: str
    verified: bool
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

    # Composer: guardrailed output (verified claims only)
    composed_answer: str

    # Evaluation
    evaluation: Dict[str, Any]

    # Misc
    metadata: Dict[str, Any]
