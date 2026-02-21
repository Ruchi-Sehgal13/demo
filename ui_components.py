"""
UI Components for Hallucination Guardrail Meta-Agent.
All render functions and custom CSS live here. app.py orchestrates them.
"""

import json
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

def inject_custom_css():
    """Inject the enterprise dark-theme CSS."""
    st.markdown("""
    <style>
    /* ── Import font ────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global overrides ───────────────────────────────── */
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: #0f1117;
    }

    /* Hide default Streamlit header / footer */
    header[data-testid="stHeader"] { background: transparent; }
    footer { display: none !important; }
    #MainMenu { visibility: hidden; }

    /* ── Card container ─────────────────────────────────── */
    .ui-card {
        background: #1a1d27;
        border: 1px solid #2a2d3a;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 12px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
    }
    .ui-card-compact {
        background: #1a1d27;
        border: 1px solid #2a2d3a;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
        box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
    }

    /* ── Top bar ────────────────────────────────────────── */
    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 0;
        margin-bottom: 8px;
        border-bottom: 1px solid #2a2d3a;
    }
    .top-bar-left {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .top-bar-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #e8eaed;
        letter-spacing: -0.02em;
    }
    .top-bar-subtitle {
        font-size: 0.72rem;
        color: #7c8091;
        font-weight: 400;
    }
    .top-bar-right {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    /* ── Badges ──────────────────────────────────────────── */
    .badge {
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        padding: 3px 10px;
        border-radius: 6px;
        text-transform: uppercase;
    }
    .badge-env {
        background: rgba(74, 144, 217, 0.15);
        color: #4A90D9;
        border: 1px solid rgba(74, 144, 217, 0.3);
    }
    .badge-supported {
        background: rgba(52, 199, 89, 0.12);
        color: #34c759;
        border: 1px solid rgba(52, 199, 89, 0.25);
    }
    .badge-contradicted {
        background: rgba(235, 87, 87, 0.12);
        color: #eb5757;
        border: 1px solid rgba(235, 87, 87, 0.25);
    }
    .badge-low-confidence {
        background: rgba(242, 201, 76, 0.12);
        color: #f2c94c;
        border: 1px solid rgba(242, 201, 76, 0.25);
    }
    .badge-unreliable {
        background: rgba(235, 87, 87, 0.08);
        color: #e07070;
        border: 1px solid rgba(235, 87, 87, 0.18);
        font-size: 0.85rem;
        padding: 5px 14px;
        border-radius: 8px;
    }
    .badge-reliable {
        background: rgba(52, 199, 89, 0.08);
        color: #34c759;
        border: 1px solid rgba(52, 199, 89, 0.18);
        font-size: 0.85rem;
        padding: 5px 14px;
        border-radius: 8px;
    }

    /* ── Status dot ─────────────────────────────────────── */
    .status-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        display: inline-block;
    }
    .status-idle     { background: #7c8091; }
    .status-running  { background: #4A90D9; animation: pulse 1.4s ease-in-out infinite; }
    .status-success  { background: #34c759; }
    .status-failed   { background: #eb5757; }

    @keyframes pulse {
      0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(74, 144, 217, 0.5); }
      50%      { opacity: 0.7; box-shadow: 0 0 0 6px rgba(74, 144, 217, 0); }
    }

    /* ── Step tracker ───────────────────────────────────── */
    .step-tracker {
        display: flex;
        align-items: center;
        gap: 6px;
        margin: 10px 0;
        flex-wrap: wrap;
    }
    .step {
        display: flex;
        align-items: center;
        gap: 5px;
        font-size: 0.75rem;
        color: #7c8091;
        font-weight: 500;
    }
    .step.done     { color: #34c759; }
    .step.active   { color: #4A90D9; }
    .step-arrow    { color: #3a3d4a; font-size: 0.7rem; }

    /* ── Metric card overrides ──────────────────────────── */
    [data-testid="stMetric"] {
        background: #1a1d27;
        border: 1px solid #2a2d3a;
        border-radius: 10px;
        padding: 14px 16px;
        box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        color: #7c8091 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #e8eaed !important;
    }

    /* ── Tabs styling ───────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        border-bottom: 1px solid #2a2d3a;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.82rem;
        font-weight: 500;
        padding: 10px 20px;
        color: #7c8091;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #4A90D9 !important;
        border-bottom: 2px solid #4A90D9 !important;
        background: transparent !important;
    }

    /* ── Sidebar styling ────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: #141620;
        border-right: 1px solid #2a2d3a;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label {
        font-size: 0.75rem !important;
        color: #9ca0b0 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-weight: 500;
    }

    /* ── Claim row ──────────────────────────────────────── */
    .claim-row {
        background: #1a1d27;
        border: 1px solid #2a2d3a;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .claim-text {
        color: #c8cad0;
        font-size: 0.88rem;
        font-weight: 400;
        line-height: 1.5;
    }
    .claim-meta {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 8px;
    }
    .claim-confidence {
        font-size: 0.72rem;
        color: #7c8091;
        font-weight: 500;
    }
    .claim-source {
        font-size: 0.68rem;
        color: #5a5e70;
    }

    /* ── Expander tweaks ────────────────────────────────── */
    .streamlit-expanderHeader {
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: #9ca0b0 !important;
    }

    /* ── Text area / input styling ──────────────────────── */
    .stTextArea textarea, .stTextInput input {
        background: #141620 !important;
        border: 1px solid #2a2d3a !important;
        border-radius: 8px !important;
        color: #e8eaed !important;
        font-size: 0.88rem !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #4A90D9 !important;
        box-shadow: 0 0 0 1px rgba(74, 144, 217, 0.3) !important;
    }

    /* ── Button overrides ───────────────────────────────── */
    .stButton > button[kind="primary"] {
        background: #4A90D9 !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        padding: 8px 24px !important;
        letter-spacing: 0.02em;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover {
        background: #5a9ee6 !important;
        box-shadow: 0 2px 8px rgba(74, 144, 217, 0.3) !important;
    }
    .stButton > button[kind="primary"]:disabled {
        background: #2a3a5a !important;
        color: #5a6a8a !important;
    }
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        color: #9ca0b0 !important;
        border: 1px solid #2a2d3a !important;
        border-radius: 8px !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        padding: 6px 16px !important;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #4A90D9 !important;
        color: #4A90D9 !important;
    }

    /* ── Progress bar ───────────────────────────────────── */
    .stProgress > div > div {
        background: #4A90D9 !important;
        border-radius: 4px;
    }

    /* ── Section title ──────────────────────────────────── */
    .section-label {
        font-size: 0.68rem;
        font-weight: 600;
        color: #5a5e70;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
    }

    /* ── Verdict display ────────────────────────────────── */
    .verdict-large {
        font-size: 1.6rem;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    .verdict-reliable   { color: #34c759; }
    .verdict-unreliable { color: #e07070; }

    /* ── Divider override ───────────────────────────────── */
    hr { border-color: #2a2d3a !important; }

    /* ── Skeleton loader ────────────────────────────────── */
    @keyframes shimmer {
        0%   { background-position: -400px 0; }
        100% { background-position: 400px 0; }
    }
    .skeleton {
        background: linear-gradient(90deg, #1a1d27 25%, #252836 50%, #1a1d27 75%);
        background-size: 800px 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 8px;
        height: 16px;
        margin: 8px 0;
    }
    .skeleton-lg  { height: 32px; width: 40%; }
    .skeleton-md  { height: 14px; width: 70%; }
    .skeleton-sm  { height: 12px; width: 50%; }

    /* ── Elapsed time ───────────────────────────────────── */
    .elapsed-time {
        font-size: 0.75rem;
        color: #7c8091;
        font-weight: 500;
        margin-top: 4px;
    }

    /* ── Predefined prompt cards ─────────────────────────── */
    .prompt-card {
        background: #161822;
        border: 1px solid #2a2d3a;
        border-radius: 10px;
        padding: 14px 16px;
        cursor: pointer;
        transition: all 0.2s ease;
        min-height: 90px;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    .prompt-card:hover {
        border-color: rgba(74, 144, 217, 0.4);
        background: #1a1e2c;
        border-left: 3px solid #4A90D9;
    }
    .prompt-card.selected {
        border-color: #4A90D9;
        background: rgba(74, 144, 217, 0.06);
        box-shadow: 0 0 0 1px rgba(74, 144, 217, 0.15);
    }
    .prompt-card-label {
        font-size: 0.62rem;
        font-weight: 600;
        color: #4A90D9;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .prompt-card-text {
        font-size: 0.78rem;
        color: #9ca0b0;
        line-height: 1.45;
        font-weight: 400;
    }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

def render_header():
    """Top bar: app name · env badge · status dot."""
    status = st.session_state.get("run_status", "idle")
    dot_class = f"status-{status}"

    st.markdown(f"""
    <div class="top-bar">
        <div class="top-bar-left">
            <div>
                <div class="top-bar-title">🛡️ Hallucination Guardrail</div>
                <div class="top-bar-subtitle">IPC ↔ BNS Verification Meta-Agent</div>
            </div>
            <span class="badge badge-env">DEV</span>
        </div>
        <div class="top-bar-right">
            <span class="status-dot {dot_class}"></span>
            <span style="font-size:0.72rem; color:#7c8091; font-weight:500;">
                {status.upper()}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def render_config(settings: dict) -> tuple[str, str]:
    """Render the sidebar config panel. Returns (provider, model)."""
    with st.sidebar:
        st.markdown("""
        <div style="padding: 8px 0 16px 0;">
            <div style="font-size:1rem; font-weight:700; color:#e8eaed; letter-spacing:-0.01em;">
                ⚙️ Configuration
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-label">LLM Provider</div>',
                    unsafe_allow_html=True)
        provider = st.selectbox(
            "LLM Provider",
            ["google", "offline", "openai", "anthropic"],
            index=["google", "offline", "openai", "anthropic"].index(
                settings["llm"]["provider"]
            ),
            help="Gemini (google) is recommended.",
            label_visibility="collapsed",
        )

        st.markdown('<div class="section-label">Model</div>',
                    unsafe_allow_html=True)
        default_model = settings["llm"]["model"] if provider == "google" else ""
        model = st.text_input(
            "Model name",
            value=default_model,
            help="Leave blank for provider default.",
            label_visibility="collapsed",
        )

        with st.expander("Advanced Settings", expanded=False):
            st.markdown(f"""
            <div style="font-size:0.75rem; color:#7c8091; line-height:1.8;">
                <b>Temperature:</b> {settings['llm'].get('temperature', 0.2)}<br>
                <b>Embedding:</b> {settings.get('embedding', {}).get('model', 'default')}<br>
                <b>Human review threshold:</b> {settings.get('verification', {}).get('human_review_confidence_threshold', 0.7)}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:24px; padding-top:16px; border-top:1px solid #2a2d3a;">
            <div class="section-label">Workflow</div>
            <div style="font-size:0.72rem; color:#7c8091; line-height:1.7;">
                1. Planner routes the query<br>
                2. Primary LLM answers<br>
                3. Claims extracted & verified<br>
                4. Low-confidence → human review
            </div>
        </div>
        """, unsafe_allow_html=True)

    return provider, model or default_model


# ─────────────────────────────────────────────────────────────────────────────
# PREDEFINED PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

_PREDEFINED_PROMPTS = [
    {
        "label": "Example 1",
        "text": "What is the BNS equivalent of IPC Section 302?",
    },
    {
        "label": "Example 2",
        "text": "List all major IPC sections that were renumbered under BNS with their new section numbers.",
    },
    {
        "label": "Example 3",
        "text": "Explain the structural differences between IPC and BNS in terms of offense categorization.",
    },
]


def render_predefined_prompts():
    """Render the Quick Start prompt cards. Sets session_state['query_input'] on click."""
    st.markdown('<div class="section-label" style="margin-bottom:6px;">Quick Start</div>',
                unsafe_allow_html=True)

    cols = st.columns(3, gap="small")
    for idx, (col, prompt) in enumerate(zip(cols, _PREDEFINED_PROMPTS)):
        with col:
            selected = st.session_state.get("selected_prompt") == idx
            sel_cls = " selected" if selected else ""

            st.markdown(f"""
            <div class="prompt-card{sel_cls}">
                <div class="prompt-card-label">{prompt["label"]}</div>
                <div class="prompt-card-text">{prompt["text"]}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Use", key=f"prompt_{idx}", type="secondary", use_container_width=True):
                st.session_state["query_input"] = prompt["text"]
                st.session_state["selected_prompt"] = idx
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# QUERY INPUT
# ─────────────────────────────────────────────────────────────────────────────

def render_query_input() -> tuple[str, bool]:
    """Render the query card. Returns (question, run_pressed)."""
    st.markdown('<div class="ui-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Query</div>',
                unsafe_allow_html=True)

    default_q = st.session_state.get(
        "query_input", "What is the BNS equivalent of IPC Section 302?"
    )
    question = st.text_area(
        "Enter your question",
        value=default_q,
        height=90,
        label_visibility="collapsed",
        placeholder="Ask a question about IPC–BNS mappings…",
    )

    col_hint, col_btn = st.columns([3, 1])
    with col_hint:
        st.markdown(
            '<span style="font-size:0.68rem; color:#5a5e70;">Ctrl + Enter to submit</span>',
            unsafe_allow_html=True,
        )
    with col_btn:
        is_running = st.session_state.get("run_status") == "running"
        run_pressed = st.button(
            "⏵ Run" if not is_running else "Running…",
            type="primary",
            disabled=is_running,
            use_container_width=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    return question, run_pressed


# ─────────────────────────────────────────────────────────────────────────────
# STATUS / STEP TRACKER
# ─────────────────────────────────────────────────────────────────────────────

_STEPS = ["Planner", "Primary LLM", "Claim Extraction", "Verification", "Final Scoring"]


def _render_step_tracker_html(completed: int):
    """Return HTML for the step-tracker with `completed` steps done."""
    parts = []
    for i, name in enumerate(_STEPS):
        if i < completed:
            cls = "step done"
            icon = "✓"
        elif i == completed:
            cls = "step active"
            icon = "●"
        else:
            cls = "step"
            icon = "○"
        parts.append(f'<span class="{cls}">{icon} {name}</span>')
        if i < len(_STEPS) - 1:
            parts.append('<span class="step-arrow">→</span>')
    return '<div class="step-tracker">' + "".join(parts) + "</div>"


def render_status(status_container):
    """Render the status card area. Returns the container for updates."""
    with status_container:
        run_status = st.session_state.get("run_status", "idle")
        if run_status == "idle":
            st.markdown("""
            <div class="ui-card-compact">
                <div class="section-label">Status</div>
                <span style="font-size:0.82rem; color:#5a5e70;">
                    Ready — submit a query to begin verification
                </span>
            </div>
            """, unsafe_allow_html=True)
        elif run_status == "running":
            step = st.session_state.get("run_step", 0)
            tracker_html = _render_step_tracker_html(step)
            st.markdown(f"""
            <div class="ui-card-compact">
                <div class="section-label">Running</div>
                {tracker_html}
            </div>
            """, unsafe_allow_html=True)
            st.progress(min(int((step / len(_STEPS)) * 100), 100))
        elif run_status == "success":
            elapsed = st.session_state.get("last_elapsed", 0)
            tracker_html = _render_step_tracker_html(len(_STEPS))
            st.markdown(f"""
            <div class="ui-card-compact">
                <div class="section-label">Complete</div>
                {tracker_html}
                <div class="elapsed-time">Completed in {elapsed:.1f}s</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(100)
        elif run_status == "failed":
            st.markdown("""
            <div class="ui-card-compact">
                <div class="section-label">Failed</div>
                <span style="font-size:0.82rem; color:#eb5757;">
                    An error occurred. Check the debug logs.
                </span>
            </div>
            """, unsafe_allow_html=True)


def render_loading_skeleton():
    """Show a shimmer skeleton while results are loading."""
    st.markdown("""
    <div class="ui-card">
        <div class="skeleton skeleton-lg"></div>
        <div class="skeleton skeleton-md"></div>
        <div class="skeleton skeleton-sm"></div>
        <div class="skeleton skeleton-md"></div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# METRICS ROW
# ─────────────────────────────────────────────────────────────────────────────

def render_metrics(final: dict):
    """Render the 4-column metrics row."""
    overall = final.get("overall_status", "").upper()
    confidence = final.get("average_confidence", 0.0)
    supported = final.get("supported_claims", 0)
    contradicted = final.get("contradicted_claims", 0)

    # Overall verdict badge
    if overall in ("RELIABLE", "SUPPORTED"):
        verdict_cls = "verdict-reliable"
        badge_cls = "badge-reliable"
    elif overall in ("UNRELIABLE", "CONTRADICTED"):
        verdict_cls = "verdict-unreliable"
        badge_cls = "badge-unreliable"
    else:
        verdict_cls = ""
        badge_cls = "badge-low-confidence"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="ui-card-compact" style="text-align:center;">
            <div class="section-label">Overall Verdict</div>
            <div class="verdict-large {verdict_cls}">{overall or "—"}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        conf_color = "#34c759" if confidence >= 0.7 else "#f2c94c" if confidence >= 0.4 else "#eb5757"
        st.markdown(f"""
        <div class="ui-card-compact" style="text-align:center;">
            <div class="section-label">Confidence</div>
            <div style="font-size:1.5rem; font-weight:700; color:{conf_color};">
                {confidence:.0%}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="ui-card-compact" style="text-align:center;">
            <div class="section-label">Supported</div>
            <div style="font-size:1.5rem; font-weight:700; color:#34c759;">
                {supported}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="ui-card-compact" style="text-align:center;">
            <div class="section-label">Contradicted</div>
            <div style="font-size:1.5rem; font-weight:700; color:#eb5757;">
                {contradicted}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS TABS
# ─────────────────────────────────────────────────────────────────────────────

def render_tabs(result: dict):
    """Render Summary · Claims · Evidence · Debug tabs."""
    final = result.get("final_result", {})

    tab_summary, tab_claims, tab_evidence, tab_debug = st.tabs(
        ["Summary", "Claims Breakdown", "Evidence", "Debug Logs"]
    )

    # ── Summary ──────────────────────────────────────────
    with tab_summary:
        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Primary LLM Response</div>',
                    unsafe_allow_html=True)
        answer = result.get("llm_answer", "")
        st.markdown(answer)

        # Copy / Download buttons
        btn_col1, btn_col2, _ = st.columns([1, 1, 4])
        with btn_col1:
            st.download_button(
                "⬇ Download Report",
                data=json.dumps(result, indent=2, default=str),
                file_name="guardrail_report.json",
                mime="application/json",
                type="secondary",
            )
        with btn_col2:
            if st.button("📋 Copy Answer", type="secondary"):
                st.code(answer, language=None)
                st.toast("Answer copied — use Ctrl+C from the box above.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Claims Breakdown ─────────────────────────────────
    with tab_claims:
        verifications = result.get("verifications", [])
        if not verifications:
            st.markdown("""
            <div class="ui-card-compact">
                <span style="font-size:0.82rem; color:#7c8091;">
                    No claims extracted — planner may have chosen the DIRECT route.
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            for i, v in enumerate(verifications, start=1):
                status = v.get("status", "unknown")
                confidence = v.get("confidence", 0)
                claim = v.get("claim", "")
                source = v.get("source", "")

                if status == "supported":
                    badge_html = '<span class="badge badge-supported">✓ Supported</span>'
                elif status == "contradicted":
                    badge_html = '<span class="badge badge-contradicted">✗ Contradicted</span>'
                else:
                    badge_html = '<span class="badge badge-low-confidence">⚠ ' + status.capitalize() + '</span>'

                conf_color = "#34c759" if confidence >= 0.7 else "#f2c94c" if confidence >= 0.4 else "#eb5757"

                st.markdown(f"""
                <div class="claim-row">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div class="claim-text"><b>Claim {i}:</b> {claim}</div>
                        {badge_html}
                    </div>
                    <div class="claim-meta">
                        <span class="claim-confidence" style="color:{conf_color};">
                            Confidence: {confidence:.0%}
                        </span>
                        <span class="claim-source">{source}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander(f"View evidence — Claim {i}", expanded=False):
                    st.markdown(v.get("evidence", "_No evidence available._"))

    # ── Evidence / Evaluation ────────────────────────────
    with tab_evidence:
        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Planner & Evaluation Details</div>',
                    unsafe_allow_html=True)

        ev_data = {
            "plan": result.get("plan"),
            "route": result.get("route"),
            "needs_human": result.get("needs_human"),
            "human_feedback": result.get("human_feedback"),
            "evaluation": result.get("evaluation"),
        }

        for key, val in ev_data.items():
            if val is not None:
                with st.expander(key.replace("_", " ").title(), expanded=False):
                    if isinstance(val, (dict, list)):
                        st.json(val)
                    else:
                        st.markdown(str(val))
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Debug Logs ───────────────────────────────────────
    with tab_debug:
        with st.expander("Raw State (JSON)", expanded=False):
            st.json(result)
