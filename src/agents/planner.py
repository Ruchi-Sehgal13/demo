from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from src.config import LLMConfig, get_llm, throttle_before_api_call
from src.graph.state import VerificationState

SYSTEM_PROMPT = """You are a planner for a hallucination-guardrail system \
verifying Indian criminal law questions (IPC ↔ BNS).

Decide:
- Whether strict verification against a trusted knowledge base is required.
- A brief natural-language plan.

Routes:
- "verify": run full pipeline (answer + claim extraction + verification).
- "direct": answer only; used for clearly non-legal or opinion questions.
"""


class PlanOutput(BaseModel):
    """Structured output for the planner (Groq/OpenAI need Pydantic or JSON schema)."""
    plan: str
    route: str


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "user",
            "User question: {question}\nReturn JSON with keys: plan (string), route (\"verify\" or \"direct\").",
        ),
    ]
)


def planner_node(state: VerificationState) -> VerificationState:
    throttle_before_api_call()
    provider = state.get("llm_provider", "groq")
    model = state.get("llm_model") or "llama-3.3-70b-versatile"
    llm = get_llm(LLMConfig(provider=provider, model=model))
    chain = prompt | llm.with_structured_output(PlanOutput)
    result = chain.invoke({"question": state["question"]})

    route = (result.route or "verify").strip().lower()
    if route not in {"verify", "direct"}:
        route = "verify"

    state["plan"] = result.plan or ""
    state["route"] = route  # type: ignore[assignment]
    return state
