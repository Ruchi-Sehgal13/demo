"""
Human validation node: based on final_result (overall_status, average_confidence), decides if the
answer needs human review. If so, appends a record to data/human_review_queue.jsonl; otherwise
marks as auto-approved. Sets state["needs_human"] and state["human_feedback"].
"""
import json
from datetime import datetime
from pathlib import Path

from src.config import paths
from src.graph.state import VerificationState


def human_validation_node(state: VerificationState) -> VerificationState:
    """
    Sets needs_human True when overall_status is unreliable/uncertain or average_confidence < 0.7.
    If needs_human: append question, answer, verifications, final_result to human_review_queue.jsonl
    and set human_feedback to "queued_for_review". Else set human_feedback to "auto-approved".
    """
    final = state.get("final_result", {})
    overall = final.get("overall_status", "unknown")
    avg_conf = float(final.get("average_confidence", 0.0))

    needs = overall in {"unreliable", "uncertain"} or avg_conf < 0.7
    state["needs_human"] = needs

    if not needs:
        state["human_feedback"] = "auto-approved"
        return state

    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "question": state.get("question"),
        "llm_answer": state.get("llm_answer"),
        "verifications": state.get("verifications", []),
        "final_result": final,
    }

    queue_path = Path(paths.ROOT) / "data" / "human_review_queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    state["human_feedback"] = "queued_for_review"
    return state
