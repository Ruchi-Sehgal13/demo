"""
LangGraph workflow: primary_llm → claim_extractor → verifier → composer → evaluation.
"""
from langgraph.graph import END, StateGraph

from src.graph.state import VerificationState
from src.nodes.agents.claim_extractor import claim_extractor_node
from src.nodes.agents.composer import composer_node
from src.nodes.agents.primary_llm import primary_llm_node
from src.nodes.agents.verifier import verifier_node
from src.nodes.steps.evaluation import evaluation_node


def create_workflow():
    """
    Build and compile the LangGraph workflow. Entry: primary_llm → claim_extractor → verifier → composer → evaluation.
    """
    g = StateGraph(VerificationState)

    g.add_node("primary_llm", primary_llm_node)
    g.add_node("claim_extractor", claim_extractor_node)
    g.add_node("verifier", verifier_node)
    g.add_node("composer", composer_node)
    g.add_node("evaluation", evaluation_node)

    g.set_entry_point("primary_llm")

    g.add_edge("primary_llm", "claim_extractor")
    g.add_edge("claim_extractor", "verifier")
    g.add_edge("verifier", "composer")
    g.add_edge("composer", "evaluation")
    g.add_edge("evaluation", END)

    return g.compile()


def run_workflow(
    question: str,
    llm_provider: str = "groq",
    llm_model: str = "llama-3.3-70b-versatile",
):
    """
    Run the full verification pipeline for one question. Initializes state with question and
    LLM settings, invokes the compiled graph, and returns the final state (answer, verifications,
    final_result, evaluation, etc.).
    """
    app = create_workflow()
    initial: VerificationState = {
        "question": question,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "metadata": {},
    }
    final_state = app.invoke(initial)
    return final_state


if __name__ == "__main__":
    q = "What is the BNS equivalent of IPC Section 302?"
    out = run_workflow(q)
    print("Question:", out["question"])
    print("Answer:", out["llm_answer"])
    print("Final:", out["final_result"])
