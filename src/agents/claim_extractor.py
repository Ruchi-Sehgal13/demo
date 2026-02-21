import re
from typing import List

from langchain_core.prompts import ChatPromptTemplate

from src.config import LLMConfig, get_llm, throttle_before_api_call
from src.graph.state import VerificationState

SYSTEM_PROMPT = """You extract atomic factual claims from a legal answer.

Rules:
- Focus on verifiable factual statements (sections, punishments, changes).
- Each claim must be self-contained and not depend on previous sentences.
- Ignore opinions, hedging, or generic statements.
- Do NOT include any introductory or meta sentences (e.g. "Here is the list of extracted claims"). Output only the factual claims themselves, one per line.

Return a numbered list of claims only (no preamble).
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("user", "Answer:\n{answer}\n\nExtract atomic claims."),
    ]
)


# Preamble/meta phrases that should not be treated as claims (case-insensitive)
_PREAMBLE_PATTERNS = [
    r"here is the list",
    r"extracted atomic (factual )?claims",
    r"the following (are )?claims",
    r"^(the )?claims (are|extracted)",
    r"^list of claims",
]
_PREAMBLE_RE = re.compile("|".join(f"({p})" for p in _PREAMBLE_PATTERNS), re.IGNORECASE)


def _is_preamble(line: str) -> bool:
    """True if the line looks like a meta/intro sentence, not a factual claim."""
    return bool(_PREAMBLE_RE.search(line))


def _parse_claims(text: str) -> List[str]:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    claims: List[str] = []
    for line in lines:
        # Strip leading numbers / bullets.
        while line and line[0] in "0123456789).-) ":
            line = line[1:].lstrip()
        if len(line) <= 5:
            continue
        if _is_preamble(line):
            continue
        claims.append(line)
    return claims


def claim_extractor_node(state: VerificationState) -> VerificationState:
    if state.get("route", "verify") == "direct":
        state["claims"] = []
        return state

    throttle_before_api_call()
    provider = state.get("llm_provider", "groq")
    model = state.get("llm_model") or "llama-3.3-70b-versatile"
    llm = get_llm(LLMConfig(provider=provider, model=model))
    chain = prompt | llm  # type: ignore[operator]
    result = chain.invoke({"answer": state["llm_answer"]})
    content = getattr(result, "content", None) or str(result)
    state["claims"] = _parse_claims(content)
    return state
