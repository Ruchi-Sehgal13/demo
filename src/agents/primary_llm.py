"""
Primary LLM node: answers the user's question using a legal-expert (IPC ↔ BNS) system prompt.
Writes the model's answer into state["llm_answer"] for downstream claim extraction and verification.
"""
from langchain_core.prompts import ChatPromptTemplate

from src.config import LLMConfig, get_llm, throttle_before_api_call
from src.graph.state import VerificationState

SYSTEM_PROMPT = """You are a legal expert on the Indian Penal Code (IPC) and the Bharatiya Nyaya Sanhita (BNS), 2023, which replaced the IPC from July 1, 2024.

When the user asks for the BNS equivalent of an IPC section (or vice versa), you MUST give a direct, specific answer with section numbers. Do not say "I am not aware" or "consult a legal expert" for standard IPC–BNS mappings.

Examples you know and must use:
- IPC Section 302 (punishment for murder) → BNS Section 103.
- IPC Section 304 → BNS Section 105 (culpable homicide not amounting to murder).
- IPC Section 376 → BNS Section 64 (punishment for rape).
- IPC Section 375 → BNS Section 63 (rape).

Rules:
- State the exact BNS (or IPC) section number in your answer, e.g. "IPC Section 302 corresponds to BNS Section 103."
- Be concise. One short paragraph is enough.
- Do not invent section numbers for sections you do not know; only for standard conversions like the examples above, give the mapping directly.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("user", "{question}"),
    ]
)


def primary_llm_node(state: VerificationState) -> VerificationState:
    """
    Runs the main LLM with the user question. Uses provider/model from state; writes the reply
    into state["llm_answer"] and returns the updated state.
    """
    throttle_before_api_call()
    provider = state.get("llm_provider", "groq")
    model = state.get("llm_model") or "llama-3.3-70b-versatile"
    llm = get_llm(LLMConfig(provider=provider, model=model))

    chain = prompt | llm  # type: ignore[operator]
    result = chain.invoke({"question": state["question"]})
    content = getattr(result, "content", None) or str(result)
    state["llm_answer"] = content
    return state
