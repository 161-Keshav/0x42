import pandas as pd
import streamlit as st

from skill_erosion.agents.divergence_scoring.agent import score_divergence
from skill_erosion.ui import (
    shell, page_header, scope_heading, load_control, select_scope, error, cohort_rows,
    summary_text, trend_facts, performance_chart, compact_chart, evidence_review,
    signal_grid, empty_state,
)


def main():
    pipeline = shell("Teacher")
    page_header("Teacher", "Learning, in perspective.",
                "Follow independent capability over time. Review the evidence, then choose the next step together.")
    load_control(pipeline)
    student, skill = select_scope(pipeline)
    review, cohort, queue = st.tabs(["Student review", "Cohort overview", "Check-in queue"])

    with review:
        with st.container(key="review_header"):
            heading, action = st.columns([3, 1], vertical_alignment="center")
            with heading:
                scope_heading(student, skill)
            with action:
                run = st.button("Run analysis", key="run_analysis", type="primary", width="stretch")
        if run:
            try:
                with st.spinner("Reviewing matched evidence and finding practice resources..."):
                    st.session_state["journey"] = pipeline.run(student, skill)
            except Exception as exc:
                error(exc)

        journey = st.session_state.get("journey")
        # This preview only reads the same matched assessment records. Semantic
        # verification, persistence and resource retrieval still require Run analysis.
        trend = journey.trend if journey else score_divergence(pipeline.repo.history(student, skill), student, skill)
        cp = trend.checkpoints
        main_column, review_column = st.columns([1.85, 1], gap="large")

        with main_column:
            with st.container(key="chart_panel"):
                st.subheader("Performance over time")
                st.caption("Matched tasks, with and without assistance.")
                if journey:
                    trend_facts(trend)
                if cp:
                    performance_chart(cp)
                    st.caption("The shaded distance shows the learning gap. Compare the pattern across checkpoints, rather than one result.")
                else:
                    empty_state("A little more history is needed",
                                "Matched assisted and independent attempts will appear here when comparable evidence is available.")
                if not journey:
                    st.caption("Assessment history only. Run analysis to verify the pattern and review practice suggestions.")

            if journey and cp:
                gap_column, hint_column = st.columns(2, gap="large")
                with gap_column:
                    st.subheader("Gap over time")
                    compact_chart([{"Checkpoint": c.checkpoint_id, "order": i, "Gap": c.gap * 100}
                                   for i, c in enumerate(cp)], "Gap", "Gap (pp)", percent=False)
                attempts = {a.evidence_id: a for a in pipeline.repo.versions(student, skill)}
                with hint_column:
                    st.subheader("Hint use")
                    compact_chart([{"Checkpoint": c.checkpoint_id, "order": i,
                                    "Hints": sum(attempts[e].hint_count > 0 for e in c.evidence_attempt_ids) / len(c.evidence_attempt_ids)}
                                   for i, c in enumerate(cp)], "Hints", "Attempts with hints", domain=[0, 1])

        with review_column:
            with st.container(key="evidence_panel"):
                st.subheader("Evidence review")
                if journey:
                    evidence_review(journey.verification)
                    st.divider()
                    st.subheader("Your next step")
                    saved = pipeline.repo.get_decision(student, skill)
                    options = ["intervene", "monitor", "dismiss"]
                    choice = st.radio("Teacher decision", options, index=options.index(saved) if saved else 1,
                                      format_func=str.title, horizontal=True, key="decision")
                    st.caption("Intervene shares the reviewed practice step. Monitor keeps the pattern visible. Dismiss suppresses recommendations.")
                    if st.button("Save decision", key="save_decision", type="primary", width="stretch"):
                        pipeline.repo.set_decision(student, skill, choice)
                        st.session_state["journey"] = pipeline.run(student, skill)
                        st.success("Decision saved and applied to the analysis.")
                        journey = st.session_state["journey"]
                    st.caption("Saved decision: " + str(pipeline.repo.get_decision(student, skill) or "awaiting review"))
                else:
                    empty_state("Start with the evidence",
                                "Run analysis to check how reliable this pattern is before choosing a next step.",
                                [("What gets reviewed", "Matched checkpoints"),
                                 ("What stays yours", "The teaching decision")])
                st.caption("Agree on a brief independent check-in, then review the matched history in one to two weeks.")

        if journey:
            with st.container(key="quality_panel"):
                st.subheader("Learning-quality signals")
                metrics = pipeline.metrics(student, skill)
                signal_grid(metrics)
                st.caption("Transfer describes co-movement, not causation. Retention needs independent follow-ups at different checkpoints.")

            st.subheader("Practice suggestions for your review")
            if not journey.clusters:
                st.write("No repeated misconception met the semantic evidence threshold.")
            for cluster in journey.clusters:
                st.write("**" + cluster.concept_summary + "**")
                with st.expander("See supporting attempts"):
                    st.caption("Evidence: " + ", ".join(cluster.evidence_attempt_ids))
            if not journey.remediation:
                st.info("No practice plan is available, or suggestions have been dismissed.")
            for i, plan in enumerate(journey.remediation):
                with st.container(border=True, key=f"teacher_plan_{i}"):
                    st.write("**" + plan.status.replace("_", " ").title() + "**")
                    if plan.teacher_summary:
                        st.write(plan.teacher_summary)
                    if plan.student_exercise:
                        st.write("**Student exercise**")
                        st.write(plan.student_exercise)

            with st.expander("Checkpoint evidence", expanded=False):
                st.caption(f"Scorer: {trend.model_version} / {journey.verification.verifier_model_version}")
                st.dataframe(pd.DataFrame([c.model_dump() for c in cp]), hide_index=True, width="stretch")
            st.download_button("Download student summary", summary_text(journey, metrics, pipeline.repo.get_decision(student, skill)),
                               file_name=f"gaptrace-{student}.txt", mime="text/plain", key="download_summary")

    with cohort:
        st.subheader("Patterns across the cohort")
        st.caption("Each row describes a student and skill. These are synthetic pilot scenarios, not population estimates.")
        if st.button("Refresh cohort overview", key="refresh_cohort"):
            st.session_state["cohort"] = cohort_rows(pipeline)
        rows = st.session_state.get("cohort", [])
        if rows:
            frame = pd.DataFrame(rows)
            st.dataframe(frame, hide_index=True, width="stretch",
                         column_config={"student": "Student", "skill": "Skill", "trend": "Trend",
                                        "verdict": "Evidence", "confidence": "Confidence", "calibration": "Calibration"})
            left, right = st.columns([1.4, 1], gap="large")
            with left:
                st.subheader("Patterns by skill")
                st.bar_chart(frame.groupby(["skill", "trend"]).size().unstack(fill_value=0))
            with right:
                st.subheader("Confidence calibration")
                st.bar_chart(frame.groupby("calibration").size().rename("histories"), color="#176b58")
        else:
            empty_state("A wider view of learning",
                        "Refresh the overview to compare patterns across students and skills.",
                        [("Available in this pilot", f"{len(pipeline.repo.students())} students"),
                         ("Reading the results", "Patterns, not rankings")])

    with queue:
        st.subheader("Student-initiated check-ins")
        st.caption("Requests for a conversation, kept separate from assessment patterns.")
        rows = pipeline.repo.checkin_queue()
        for sid in pipeline.repo.students():
            rows += [dict(trace_id=a.evidence_id, student_id=sid, skill_id=a.skill_id, timestamp=a.timestamp, origin=a.origin)
                     for a in pipeline.repo.history(sid) if a.origin == "student_initiated"]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        else:
            empty_state("No requests waiting", "When a student asks for a check-in, their request will appear here.")


main()
