"""
Composer node: builds the guardrailed output by asking an LLM to answer the user's question
using only verified claims. If verified claims don't suffice, the LLM returns a refusal message.
"""
from langchain_core.prompts import ChatPromptTemplate

from src.config import LLMConfig, get_llm, throttle_before_api_call
from src.graph.state import VerificationState

COMPOSER_SYSTEM = """You are a guardrail for a legal Q&A system. You must answer using ONLY the verified claims provided. Do not add any information that is not in the verified claims.

If the verified claims are enough to answer the user's question, write a single short paragraph that answers it.
If the verified claims do NOT allow you to answer the user's question (e.g. they are off-topic or too generic), you must respond with exactly this sentence and nothing else:

I could not find reference for this in the knowledge base.

Do not add explanations, apologies, or extra text when refusing. Do not use the verified claims to infer or invent an answer."""

COMPOSER_USER = """User question: {question}

Verified claims from the knowledge base (use only these):
{verified_claims}

Write a single short paragraph that answers the user's question using ONLY the verified claims above. If you cannot answer the question from these claims alone, respond with exactly: I could not find reference for this in the knowledge base."""

REFUSAL_SENTENCE = "I could not find reference for this in the knowledge base."


def composer_node(state: VerificationState) -> VerificationState:
    """
    Reads state["verifications"] and state["question"]. If there are verified claims, calls an LLM
    to produce a short answer to the question using only those claims, or the refusal sentence.
    Sets state["composed_answer"].
    """
    question = state.get("question", "")
    verifications = state.get("verifications", [])
    verified_claims = [v["claim"] for v in verifications if v.get("verified")]

    if not verified_claims:
        if not verifications:
            state["composed_answer"] = (
                "No claims could be extracted for verification. No guardrailed output."
            )
        else:
            state["composed_answer"] = REFUSAL_SENTENCE
        return state

    # Format verified claims for the prompt
    claims_text = "\n".join(f"{i}. {c}" for i, c in enumerate(verified_claims, start=1))

    throttle_before_api_call()
    provider = state.get("llm_provider", "groq")
    model = state.get("llm_model") or "llama-3.3-70b-versatile"
    llm = get_llm(LLMConfig(provider=provider, model=model))
    prompt = ChatPromptTemplate.from_messages(
        [("system", COMPOSER_SYSTEM), ("user", COMPOSER_USER)]
    )
    chain = prompt | llm
    response = chain.invoke({"question": question, "verified_claims": claims_text})
    content = getattr(response, "content", None) or str(response)
    composed = (content or "").strip()

    # Normalize refusal: if the model said something equivalent, use the canonical sentence
    if "could not find reference" in composed.lower() or "could not verify" in composed.lower():
        composed = REFUSAL_SENTENCE

    state["composed_answer"] = composed
    return state
