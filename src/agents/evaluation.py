"""
Evaluation node: appends one JSONL line per run to data/eval_log.jsonl (timestamp, question,
plan, route, overall_status, average_confidence, claim counts). Used for offline metrics; does not
change the answer. Sets state["evaluation"] to the logged dict.
"""
import json
from datetime import datetime
from pathlib import Path

from src.config import paths
from src.graph.state import VerificationState


def evaluation_node(state: VerificationState) -> VerificationState:
    """
    Builds a log dict from state (question, plan, route, final_result stats) and appends it to
    paths.EVAL_LOG. Writes the same dict to state["evaluation"] and returns state.
    """
    final = state.get("final_result", {})
    log = {
        "timestamp": datetime.utcnow().isoformat(),
        "question": state.get("question"),
        "plan": state.get("plan"),
        "route": state.get("route"),
        "overall_status": final.get("overall_status"),
        "average_confidence": final.get("average_confidence"),
        "counts": {
            "supported": final.get("supported_claims"),
            "weak_evidence": final.get("weak_evidence_claims", 0),
            "no_evidence": final.get("no_evidence_claims", 0),
            "contradicted": final.get("contradicted_claims"),
            "uncertain": final.get("uncertain_claims"),
            "total": final.get("total_claims"),
        },
    }

    p = Path(paths.EVAL_LOG)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    state["evaluation"] = log
    return state
