from dotenv import load_dotenv
load_dotenv()
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from src.graph.workflow import run_workflow  # noqa: E402

st.set_page_config(
    page_title="Hallucination Guardrail – IPC/BNS",
    page_icon="🛡️",
    layout="wide",
)

st.title("Hallucination Guardrail Meta‑Agent (IPC ↔ BNS)")
st.markdown(
    "Meta‑agent that breaks LLM responses into claims and verifies them against "
    "a trusted IPC–BNS knowledge base (vector store)."
)

with st.sidebar:
    st.header("Configuration")

    provider = st.selectbox(
        "LLM Provider",
        ["groq", "google"],
        index=1,
        help="Groq or Google (Gemini) for answers.",
    )

    if provider == "groq":
        default_model = "llama-3.3-70b-versatile"
    else:
        default_model = "gemini-2.5-flash"
    model = st.text_input(
        "Model name",
        value=default_model,
        help="Leave blank for provider default (except Gemini).",
    )

    st.markdown("---")
    st.markdown(
        "**Workflow**\n\n"
        "1. Primary LLM answers the question.\n"
        "2. Claims are extracted; each is verified by semantic search + LLM (true/false).\n"
        "3. Composer outputs only verified claims (guardrailed answer).\n"
        "4. All runs are logged."
    )

st.markdown("---")
col1, col2 = st.columns([2, 1])

with col1:
    question = st.text_area(
        "Ask a question",
        "What is the BNS equivalent of IPC Section 302?",
        height=120,
    )
    run_btn = st.button("Run Guardrail", type="primary", use_container_width=True)

with col2:
    st.subheader("Run Status")
    status_placeholder = st.empty()
    progress = st.progress(0)

if run_btn and question.strip():
    try:
        status_placeholder.info("Running primary LLM and verification...")
        progress.progress(25)
        result = run_workflow(
            question.strip(),
            llm_provider=provider,
            llm_model=model or default_model,
        )
        progress.progress(100)
        st.session_state["last_result"] = result
        status_placeholder.success("Verification complete.")
    except Exception as e:
        status_placeholder.error(f"Error: {e}")
        st.exception(e)
        result = None
else:
    result = st.session_state.get("last_result")

if result:
    final = result.get("final_result", {})

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Guardrailed Answer", "Verification", "Evidence / Evaluation", "Debug"]
    )

    with tab1:
        st.subheader("Guardrailed Answer (verified against KB only)")
        st.markdown(result.get("composed_answer", "_No composed answer._"))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall Status", final.get("overall_status", "").upper())
        c2.metric("Verified", final.get("verified_claims", 0))
        c3.metric("Not verified", final.get("not_verified_claims", 0))
        c4.metric("Total claims", final.get("total_claims", 0))

        with st.expander("Full LLM response (unfiltered)"):
            st.markdown(result.get("llm_answer", ""))

    with tab2:
        st.subheader("Claim‑by‑Claim Verification")
        verifications = result.get("verifications", [])
        if not verifications:
            st.info("No claims extracted.")
        else:
            for i, v in enumerate(verifications, start=1):
                verified = v.get("verified", False)
                icon = "✅" if verified else "❌"
                label = "Verified" if verified else "Not verified"
                with st.container():
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"**Claim {i}:** {v['claim']}")
                    c2.markdown(f"{icon} **{label}**")
                    with st.expander("View evidence from KB"):
                        st.write(v.get("evidence", ""))
                st.divider()

    with tab3:
        st.subheader("Evaluation")
        st.json(result.get("evaluation", {}))

    with tab4:
        st.subheader("Raw State (Debug)")
        st.json(result)
else:
    st.info("Enter a question and click **Run Guardrail** to start.")
