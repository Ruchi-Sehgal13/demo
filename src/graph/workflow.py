import asyncio

from langgraph.graph import END, START, StateGraph

from src.agents.claim_extractor import claim_extractor_node
from src.agents.evaluation import evaluation_node
from src.agents.human_validation import human_validation_node
from src.agents.planner import planner_node
from src.agents.primary_llm import primary_llm_node
from src.agents.verifier import verifier_node
from src.config import settings
from src.graph.state import VerificationState


def create_workflow():
    g = StateGraph(VerificationState)

    g.add_node("planner", planner_node)
    g.add_node("primary_llm", primary_llm_node)
    g.add_node("claim_extractor", claim_extractor_node)
    g.add_node("verifier", verifier_node)
    g.add_node("human_validation", human_validation_node)
    g.add_node("evaluation", evaluation_node)

    # Fan-out: planner and primary_llm run in PARALLEL from START
    g.add_edge(START, "planner")
    g.add_edge(START, "primary_llm")

    def _should_verify(state: VerificationState) -> bool:
        return state.get("route", "verify") == "verify"

    # Both must complete before routing decision
    # LangGraph waits for all incoming edges before executing conditional
    g.add_conditional_edges(
        "planner",
        _should_verify,
        {
            True: "claim_extractor",
            False: "evaluation",
        },
    )

    # primary_llm also feeds into claim_extractor (provides llm_answer)
    g.add_edge("primary_llm", "claim_extractor")

    g.add_edge("claim_extractor", "verifier")
    g.add_edge("verifier", "human_validation")
    g.add_edge("human_validation", "evaluation")
    g.add_edge("evaluation", END)

    return g.compile()


_compiled_workflow = None


async def _run_workflow_async(
    question: str,
    llm_provider: str = settings["llm"]["provider"],
    llm_model: str = settings["llm"]["model"],
):
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = create_workflow()
    initial: VerificationState = {
        "question": question,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "metadata": {},
    }
    final_state = await _compiled_workflow.ainvoke(initial)
    return final_state


def run_workflow(
    question: str,
    llm_provider: str = settings["llm"]["provider"],
    llm_model: str = settings["llm"]["model"],
):
    """Sync wrapper for Streamlit compatibility."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in an async context (e.g. Streamlit with async)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(
                asyncio.run,
                _run_workflow_async(question, llm_provider, llm_model)
            ).result()
    else:
        return asyncio.run(
            _run_workflow_async(question, llm_provider, llm_model)
        )


if __name__ == "__main__":
    q = "What is the BNS equivalent of IPC Section 302?"
    out = run_workflow(q)
    print("Question:", out["question"])
    print("Answer:", out["llm_answer"])
    print("Final:", out["final_result"])
