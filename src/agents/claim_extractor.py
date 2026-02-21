import logging
from typing import List

from langchain_core.prompts import ChatPromptTemplate

from src.config import LLMConfig, get_llm
from src.graph.state import VerificationState
from src.agents.utils import extract_text

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You extract atomic factual claims from a legal answer.

Rules:
- Focus on verifiable factual statements (sections, punishments, changes).
- Each claim must be self-contained and not depend on previous sentences.
- Ignore opinions, hedging, or generic statements.

Return a numbered list of claims.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("user", "Answer:\n{answer}\n\nExtract atomic claims."),
    ]
)


def _parse_claims(text: str) -> List[str]:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    claims: List[str] = []
    for line in lines:
        # Strip leading numbers / bullets.
        while line and line[0] in "0123456789).-) ":
            line = line[1:].lstrip()
        if len(line) > 5:
            claims.append(line)
    return claims


def claim_extractor_node(state: VerificationState) -> VerificationState:
    if state.get("route", "verify") == "direct":
        state["claims"] = []
        return state

    try:
        llm = get_llm(LLMConfig())
        chain = prompt | llm  # type: ignore[operator]
        result = chain.invoke({"answer": state["llm_answer"]})
        content = extract_text(result)
        state["claims"] = _parse_claims(content)
    except Exception as e:
        logger.error("Claim extraction failed: %s", e, exc_info=True)
        state["claims"] = []

    return state
