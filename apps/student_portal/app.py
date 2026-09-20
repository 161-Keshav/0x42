from time import monotonic
import streamlit as st
from skill_erosion.config import skill_map
from skill_erosion.ui import shell, page_header, scope_heading, load_control, select_scope, error, empty_state
from skill_erosion.assessments import QUESTIONS, submit_retest


def main():
    pipeline = shell("Student")
    page_header("Student", "Make the next step your own.",
                "See what your practice tells you, ask for support, and try a short independent check-in.")
    load_control(pipeline)
    student, skill = select_scope(pipeline)
    practice, retest = st.tabs(["Your practice step", "Independent check-in"])

    with practice:
        learning, support = st.columns([1.85, 1], gap="large")
        with learning:
            with st.container(key="practice_panel"):
                scope_heading(student, skill)
                if st.button("Request a personalized practice step", key="request_practice", type="primary"):
                    try:
                        with st.spinner("Reviewing your learning history..."):
                            journey = pipeline.run(student, skill)
                            st.session_state["journey"] = journey
                            plans = pipeline.student_plans(journey)
                            st.session_state["shown_plan"] = next((p for p in plans if p.status == "ready"), None)
                            st.session_state["excluded_resources"] = []
                    except Exception as exc:
                        error(exc)
                journey = st.session_state.get("journey")
                if journey:
                    st.subheader(journey.explanation.headline)
                    st.write(journey.explanation.explanation)
                    with st.expander("What your practice shows"):
                        for point in journey.explanation.evidence_points:
                            st.write("• " + point)
                    st.write("**Next step:** " + journey.explanation.next_step)
                    plan = st.session_state.get("shown_plan")
                    if plan and pipeline.repo.get_decision(student, skill) == "intervene":
                        if plan.status == "ready":
                            st.divider()
                            st.subheader("A practice step reviewed by your teacher")
                            st.write(plan.student_exercise)
                            with st.expander("Practice source"):
                                st.caption("Source resource: " + ", ".join(plan.resource_ids))
                            if st.button("This exercise did not help", key="alternative"):
                                excluded = list(dict.fromkeys(st.session_state.get("excluded_resources", []) + plan.resource_ids))
                                st.session_state["excluded_resources"] = excluded
                                try:
                                    st.session_state["shown_plan"] = pipeline.alternative(journey, excluded)
                                    st.rerun()
                                except Exception as exc:
                                    error(exc)
                        else:
                            st.info("No other matching resource is available. Ask your teacher to choose a different approach.")
                    else:
                        st.info("Your teacher can review the evidence and approve a personalized practice step. You can still request a check-in.")
                else:
                    empty_state("One manageable next step",
                                "Use your recent practice to find a focused exercise. Your teacher reviews it before it is shared with you.",
                                [("Current focus", skill_map()[skill]["name"]),
                                 ("After practice", "Try an independent check-in")])

        with support:
            with st.container(key="support_panel"):
                st.subheader("Something feels off?")
                st.write("You do not need to wait for a result to ask for help.")
                st.caption("A check-in request lets your teacher know you would like a conversation. It does not change your assessment results.")
                if st.button("Request a check-in", key="request_checkin", width="stretch"):
                    pipeline.repo.request_checkin(student, skill)
                    st.success("Your check-in request is in your teacher's review queue.")
            st.caption("Learning takes practice. A gap is a starting point for a conversation, not a label.")

    with retest:
        with st.container(key="retest_sheet"):
            st.subheader("Try it independently")
            st.caption("Three short questions. Work without assistance. No screen recording or monitoring is used.")
            st.session_state.setdefault("quiz_started", monotonic())
            with st.form("retest"):
                answers = []
                for i, (question, choices, _) in enumerate(QUESTIONS[skill]):
                    st.caption(f"Question {i + 1} of {len(QUESTIONS[skill])}")
                    answers.append(st.radio(question, choices, index=None, key=f"answer_{i}"))
                    if i < len(QUESTIONS[skill]) - 1:
                        st.divider()
                confidence = st.slider("How confident do you feel about these answers?", 0.0, 1.0, .5, .1, key="self_confidence")
                submitted = st.form_submit_button("Submit independent retest", type="primary")
            if submitted:
                if any(a is None for a in answers):
                    st.warning("Answer all three questions before submitting.")
                else:
                    try:
                        result = submit_retest(pipeline.repo, student, skill, answers, confidence,
                                               monotonic() - st.session_state["quiz_started"])
                        st.session_state["retest_result"] = result
                        st.session_state["journey"] = pipeline.run(student, skill)
                        st.session_state["quiz_started"] = monotonic()
                    except Exception as exc:
                        error(exc)
            result = st.session_state.get("retest_result")
            if result:
                before, current = result["previous_independent_score"], result["independent_score"]
                st.metric("Independent retest", f"{current:.0%}",
                          f"{(current-before)*100:+.1f} pp" if before is not None else None)
                st.caption("Change is descriptive: these practice questions may differ in difficulty from the earlier assessment.")
                st.info(result["gap_message"])


main()
