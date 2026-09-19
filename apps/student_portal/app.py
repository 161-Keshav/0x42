"""Run: python -m streamlit run apps/student_portal/app.py --server.port 8502."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

from skill_erosion.contracts.models import Attempt
from skill_erosion.data import (
    load_expected_trends,
    load_resource_body,
    load_resource_catalog,
    load_synthetic_attempts,
)
from skill_erosion.agents.remediation.agent import recommend_remediation
from skill_erosion.logging_utils import get_logger
from skill_erosion.orchestration.pipeline import run_journey
from skill_erosion.storage import default_repository

logger = get_logger("student_portal", separate_file=True)

st.set_page_config(page_title="Student | Skill Erosion Tracker")
st.title("Your next practice step")
st.caption("Demo view over synthetic data. You only see the selected learner's own plan.")

expected = load_expected_trends()
students = sorted(expected)

if "seeded" not in st.session_state:
    st.session_state.seeded = False

if st.button("Load / refresh synthetic data", type="primary"):
    from skill_erosion.agents.trace_collector.agent import collect_traces

    try:
        collect_traces(load_synthetic_attempts())
        st.session_state.seeded = True
        st.success("Synthetic data ready.")
        st.toast("Synthetic data loaded", icon="📥")
    except Exception as exc:
        logger.exception("seed failed")
        st.error(f"Failed to load data: {exc}")
        st.toast("Could not load data", icon="❌")

student_id = st.selectbox("Learner", students)
skill_id = expected[student_id]["skill_id"]

if not st.session_state.seeded:
    st.info("Load the synthetic data first.")

if st.session_state.seeded and st.button("Get my practice step"):
    try:
        st.session_state.result = asyncio.run(run_journey(None, student_id, skill_id))
        st.toast("Plan ready", icon="✅")
    except Exception as exc:
        logger.exception("analysis failed for %s", student_id)
        st.error(f"Failed to build your plan: {exc}")
        st.toast("Plan failed - see log", icon="❌")

if st.session_state.seeded and st.button("Something feels off - request a check-in"):
    from skill_erosion.agents.trace_collector.agent import collect_traces
    from skill_erosion.storage import default_repository

    history = default_repository().history(student_id, skill_id)
    n = len([a for a in history if a.origin == "student_initiated"]) + 1
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    collect_traces(
        [
            Attempt(
                attempt_id=f"{student_id}-student-flag-{n}",
                version=1,
                student_id=student_id,
                skill_id=skill_id,
                task_id=f"student-initiated-checkin-{n}",
                matched_task_set_id=f"student-initiated-{n}",
                checkpoint_id=f"student-checkin-{n}",
                timestamp=now,
                assistance="unassisted",
                task_type="written",
                response_text="Student requested a mentor check-in.",
                correctness=0.0,
                time_taken_seconds=0,
                hint_count=0,
                rubric_version="student-checkin-v1",
                synthetic=True,
                origin="student_initiated",
            )
        ]
    )
    st.toast("Check-in request sent to your teacher", icon="📣")
    st.info("Your teacher can now review this request alongside your trend.")

result = st.session_state.get("result")
if st.session_state.seeded and result is not None:
    explanation = result.explanation

    st.subheader("Why am I seeing this?")
    st.write(f"**{explanation.headline}**")
    st.write(explanation.plain_language)
    with st.expander("My check-in history"):
        import pandas as pd

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "checkpoint": point.checkpoint_id,
                        "assisted": point.assisted_score,
                        "unassisted": point.unassisted_score,
                        "gap": point.gap,
                    }
                    for point in result.trend.checkpoints
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        for point in explanation.evidence_points:
            st.write(f"- {point}")
    st.write(f"**Next step:** {explanation.next_step}")

    ready = [p for p in result.remediation if p.status == "ready"]
    if not ready:
        st.write(
            "No targeted exercise yet. "
            "Keep completing the weekly unassisted checkpoints so a plan can be built."
        )
    else:
        plan = ready[0]
        cluster = next(c for c in result.clusters if c.cluster_id == plan.cluster_id)
        st.subheader(cluster.concept_summary)
        st.write(plan.student_exercise)
        if st.button("This exercise did not help"):
            alternative = recommend_remediation(
                cluster,
                result.trend,
                excluded_resource_ids=plan.resource_ids,
            )
            if alternative.status == "ready":
                st.session_state.alternative_plan = alternative
                st.toast("A different exercise is ready", icon="🔁")
            else:
                st.info("There is no different curated exercise for this skill yet.")
        alternative_plan = st.session_state.get("alternative_plan")
        if alternative_plan is not None and alternative_plan.cluster_id == cluster.cluster_id:
            st.info("Alternative exercise")
            st.write(alternative_plan.student_exercise)
        catalog = {r["resource_id"]: r for r in load_resource_catalog()}
        for resource_id in plan.resource_ids:
            resource = catalog.get(resource_id)
            if resource:
                with st.expander(f"Resource: {resource_id}"):
                    st.markdown(load_resource_body(resource))

        st.divider()
        st.subheader("Follow-up check (unassisted)")
        st.caption(
            "Answer without any tools. This becomes your next checkpoint and shows "
            "whether the gap narrowed after practice."
        )
        follow_up_questions = [
            (
                "What does `list(range(1, 5))` return?",
                ["[1, 2, 3, 4]", "[1, 2, 3, 4, 5]", "[0, 1, 2, 3, 4]"],
                "[1, 2, 3, 4]",
            ),
            (
                "What does `list(range(2, 6, 2))` return?",
                ["[2, 4]", "[2, 4, 6]", "[0, 2, 4]"],
                "[2, 4]",
            ),
            (
                "Which value is excluded by `range(3, 6)`?",
                ["3", "5", "6"],
                "6",
            ),
        ]
        question_index = len(default_repository().history(student_id, skill_id)) % len(follow_up_questions)
        question, options, correct_answer = follow_up_questions[question_index]
        answer = st.radio(
            question,
            options,
            index=None,
        )
        seconds = st.number_input("Seconds you spent", min_value=5, max_value=3600, value=120)
        if st.button("Submit follow-up"):
            if answer is None:
                st.error("Pick an answer first.")
            else:
                from skill_erosion.agents.trace_collector.agent import collect_traces

                history = default_repository().history(student_id, skill_id)
                followups = [a for a in history if a.task_id.startswith("followup-")]
                n = len(followups) + 1
                week = len({a.checkpoint_id for a in history}) + 1
                attempt = Attempt(
                    attempt_id=f"{student_id}-followup-{n}",
                    version=1,
                    student_id=student_id,
                    skill_id=skill_id,
                    task_id=f"followup-{n}-unassisted",
                    matched_task_set_id=f"followup-{n}",
                    checkpoint_id=f"week-{week}",
                    timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    assistance="unassisted",
                    task_type="quiz",
                    response_text=f"Follow-up answer: {answer}",
                    correctness=1.0 if answer == correct_answer else 0.0,
                    time_taken_seconds=int(seconds),
                    hint_count=0,
                    rubric_version="loops-rubric-v1",
                    synthetic=True,
                    similarity_to_prior=None,
                    origin="follow_up",
                )
                collect_traces([attempt])
                previous = [c.unassisted_score for c in result.trend.checkpoints]
                new_score = 0.6 * attempt.correctness + 0.4 * max(0.0, 1.0 - attempt.time_taken_seconds / 600)
                if previous:
                    delta = new_score - previous[-1]
                    direction = "narrowed" if delta > 0 else "did not narrow"
                    msg = (
                        f"Follow-up recorded. Your independent score moved from "
                        f"{previous[-1]:.2f} to {new_score:.2f} - the gap {direction}."
                    )
                    st.info(msg)
                    st.toast(f"Gap {direction}", icon="📉" if delta > 0 else "📈")
                else:
                    st.info(f"Follow-up recorded. Independent score: {new_score:.2f}.")
                    st.toast("Follow-up recorded", icon="✅")
                st.session_state.result = asyncio.run(run_journey(None, student_id, skill_id))
                st.rerun()
