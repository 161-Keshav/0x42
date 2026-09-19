"""Run: python -m streamlit run apps/parent_portal/app.py --server.port 8503."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

from skill_erosion.data import load_expected_trends, load_synthetic_attempts
from skill_erosion.agents.parent_chat.agent import answer_parent_question
from skill_erosion.metrics import calculate_metrics
from skill_erosion.logging_utils import get_logger
from skill_erosion.orchestration.pipeline import run_journey
from skill_erosion.storage import default_repository

logger = get_logger("parent_portal", separate_file=True)

st.set_page_config(page_title="Parent | Skill Erosion Tracker")
st.title("Family learning update")
st.caption("Supportive progress information for one linked learner.")

expected = load_expected_trends()
students = sorted(expected)
repository = default_repository()
if not repository.parent_accounts():
    repository.link_parent("demo-parent", students[0])
parent_id = st.selectbox("Parent account", repository.parent_accounts())
student_id = repository.get_linked_student(parent_id)
skill_id = expected[student_id]["skill_id"]

def ensure_demo_data() -> bool:
    from skill_erosion.agents.trace_collector.agent import collect_traces

    try:
        result = collect_traces(load_synthetic_attempts())
        st.session_state.parent_data_loaded = True
        st.toast(f"Learning update refreshed ({len(result.attempt_ids)} attempts)", icon="📥")
        return True
    except Exception as exc:
        logger.exception("parent data load failed")
        st.error(f"Could not load the learning data: {exc}")
        st.toast("Learning data could not be loaded", icon="❌")
        return False

if "parent_data_loaded" not in st.session_state:
    st.session_state.parent_data_loaded = False

if st.button("Load / refresh synthetic data", type="primary"):
    ensure_demo_data()

if st.button("View learning update"):
    attempts = default_repository().history(student_id, skill_id)
    if not attempts and not ensure_demo_data():
        st.stop()
    attempts = default_repository().history(student_id, skill_id)
    try:
        with st.spinner("Preparing the linked learner's update..."):
            st.session_state.parent_result = asyncio.run(
                run_journey(None, student_id, skill_id)
            )
        st.session_state.parent_result_scope = (student_id, skill_id)
        st.toast("Learning update ready", icon="✅")
    except Exception as exc:
        logger.exception("parent update failed for %s/%s", student_id, skill_id)
        st.error(f"Could not prepare this learning update: {exc}")
        st.toast("Learning update failed - see the parent portal log", icon="❌")

def prepare_parent_result() -> bool:
    """Load the linked learner and build the scoped journey for chat."""
    attempts = default_repository().history(student_id, skill_id)
    if not attempts and not ensure_demo_data():
        return False
    try:
        with st.spinner("Preparing the linked learner's update..."):
            st.session_state.parent_result = asyncio.run(
                run_journey(None, student_id, skill_id)
            )
        st.session_state.parent_result_scope = (student_id, skill_id)
        return True
    except Exception as exc:
        logger.exception("parent chat preparation failed for %s/%s", student_id, skill_id)
        st.error(f"Could not prepare the chat context: {exc}")
        return False

st.subheader("Ask the family learning assistant")
st.caption(
    "RAG assistant: answers use the linked learner's update and "
    "teacher-curated practice resources. It does not expose internal scores "
    "or other learners' information."
)
with st.form("parent-chat-form", clear_on_submit=False):
    question = st.text_input(
        "Ask about this learning update",
        key="parent-question",
        placeholder="What should we practice next?",
    )
    submitted = st.form_submit_button("Ask assistant", type="primary")

if submitted:
    if not question.strip():
        st.warning("Type a question before asking the assistant.")
    elif prepare_parent_result():
        st.session_state.parent_pending_question = question.strip()
        st.rerun()

result = st.session_state.get("parent_result")
if result is not None and st.session_state.get("parent_result_scope") == (student_id, skill_id):
    attempts = default_repository().history(student_id, skill_id)
    metrics = calculate_metrics(attempts)
    if result.trend.status in {"narrowing", "stable"}:
        standing = f"{student_id} is showing steady independent progress in {skill_id}."
    elif result.trend.status == "widening":
        standing = (
            f"{student_id} has an area to keep an eye on in {skill_id}; "
            "independent work is not keeping pace with supported work yet."
        )
    else:
        standing = f"There is not enough consistent evidence yet to describe {skill_id}."

    st.subheader("How things are going")
    st.write(standing)
    st.write(
        f"The recent pattern is **{result.trend.status.replace('_', ' ')}**. "
        "This is a learning signal, not a judgment about effort or honesty."
    )
    ready = [p for p in result.remediation if p.status == "ready"]
    if ready:
        st.info(
            "The teacher already has a targeted practice step available, so "
            "extra pressure or duplicate worksheets are not necessary."
        )
        st.write("A helpful home action: set aside ten minutes for unassisted practice.")
    else:
        st.info("No targeted practice is assigned yet; regular short practice is enough.")
    with st.expander("What the data says"):
        st.write(
            f"The update is based on {len(result.trend.checkpoints)} paired check-ins over time."
        )
        st.metric("Independent check-ins", metrics["unassisted_attempts"])
        st.metric("Follow-up check-ins", metrics["follow_up_attempts"])
        st.caption(
            "The portal intentionally does not show internal verifier confidence, "
            "raw misconception labels, or comparisons with other students."
        )
    pending_question = st.session_state.pop("parent_pending_question", None)
    if pending_question:
        try:
            with st.spinner("Searching the linked update and curated resources..."):
                answer = answer_parent_question(pending_question, result)
            st.success(answer)
        except Exception as exc:
            logger.exception("parent RAG answer failed for %s/%s", student_id, skill_id)
            st.error(
                "The update loaded, but resource retrieval failed. "
                f"Details: {exc}"
            )
else:
    st.info("Submit a question. The linked update will be loaded automatically.")
