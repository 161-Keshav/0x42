"""Run: python -m streamlit run apps/teacher_dashboard/app.py --server.port 8501."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

from skill_erosion.data import load_expected_trends, load_synthetic_attempts
from skill_erosion.agents.remediation.agent import recommend_remediation
from skill_erosion.logging_utils import get_logger
from skill_erosion.orchestration.pipeline import run_journey
from skill_erosion.storage import default_repository

logger = get_logger("teacher_dashboard", separate_file=True)

st.set_page_config(page_title="Teacher | Skill Erosion Tracker", layout="wide")
st.title("Teacher trend dashboard")
st.caption(
    "Pipeline: trace collector -> divergence scorer -> verifier -> misconception "
    "clusterer -> remediation. Synthetic pilot data only."
)

expected = load_expected_trends()
students = sorted(expected)

if "seeded" not in st.session_state:
    st.session_state.seeded = False

col_seed, _ = st.columns([1, 3])
if col_seed.button("Load / refresh synthetic data", type="primary"):
    from skill_erosion.agents.trace_collector.agent import collect_traces

    try:
        result = collect_traces(load_synthetic_attempts())
        st.session_state.seeded = True
        st.success(f"Stored {len(result.attempt_ids)} attempts ({result.stored_versions} versions). Reimport is a no-op.")
        st.toast(f"Ingested {len(result.attempt_ids)} attempts", icon="📥")
    except Exception as exc:
        logger.exception("seed failed")
        st.error(f"Failed to load data: {exc}")
        st.toast("Could not load data", icon="❌")

student_id = st.selectbox("Student", students)
skill_id = expected[student_id]["skill_id"]

if not st.session_state.seeded:
    st.info("Load the synthetic data first.")

if st.session_state.seeded and st.button("Show cohort roll-up"):
    rows = []
    for cohort_student in students:
        cohort_skill = expected[cohort_student]["skill_id"]
        cohort_result = asyncio.run(run_journey(None, cohort_student, cohort_skill))
        rows.append(
            {
                "student": cohort_student,
                "skill": cohort_skill,
                "trend": cohort_result.trend.status,
                "verdict": cohort_result.verification.verdict,
                "confidence": cohort_result.verification.confidence,
            }
        )
    import pandas as pd

    st.subheader("Cohort roll-up")
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    counts = (
        pd.DataFrame(rows)
        .groupby(["skill", "trend"])
        .size()
        .reset_index(name="students")
    )
    st.dataframe(counts, use_container_width=True, hide_index=True)


def suggestion_from(verification, trend) -> str:
    if verification.verdict == "confirmed" and verification.confidence == "medium":
        return "Add one more unassisted checkpoint to raise confidence to high."
    if verification.verdict == "confirmed":
        return "Assign the remediation plan and schedule the day-two follow-up check."
    if trend.status == "insufficient_data":
        return "Complete more weekly checkpoints so a fair trend can be computed."
    return "Hold this flag: the movement looks like noise. Wait for the next checkpoint."

if st.session_state.seeded and st.button("Run analysis"):
    try:
        result = asyncio.run(run_journey(None, student_id, skill_id))
        st.session_state.teacher_result = result
        st.session_state.teacher_result_scope = (student_id, skill_id)
    except Exception as exc:
        logger.exception("analysis failed for %s", student_id)
        st.error(f"Analysis failed: {exc}")
        st.toast("Analysis failed - see log", icon="❌")
        st.stop()

    trend = result.trend
    verification = result.verification
    decision = default_repository().get_teacher_decision(student_id, skill_id)

    st.subheader(f"{student_id} - {skill_id}")

    if verification.verdict == "confirmed":
        st.success(f"Verifier: flag CONFIRMED ({verification.confidence} confidence)")
        st.toast(f"Flag confirmed ({verification.confidence} confidence)", icon="✅")
    else:
        st.warning(f"Verifier: flag DOWNGRADED ({verification.confidence} confidence)")
        st.toast(f"Flag downgraded ({verification.confidence} confidence)", icon="⚠️")
    for reason in verification.reasons:
        st.write(f"- {reason}")
    suggested_update = suggestion_from(verification, trend)
    st.info(f"**Suggested update:** {suggested_update}")
    st.toast(f"Next update: {suggested_update}", icon="🛠️")

    st.markdown("**Mentor decision**")
    decision_cols = st.columns(3)
    for column, label in zip(decision_cols, ("intervene", "monitor", "dismiss")):
        if column.button(label.title(), key=f"decision-{label}"):
            default_repository().set_teacher_decision(student_id, skill_id, label)
            st.session_state.teacher_decision = label
            st.toast(f"Decision saved: {label}", icon="📝")
            decision = label
    if decision:
        st.caption(f"Saved decision: **{decision}**. It will be applied on the next analysis.")

    status_col, gap_col, model_col = st.columns(3)
    status_col.metric("Trend status", trend.status)
    if trend.checkpoints:
        gap_col.metric("Latest gap", f"{trend.checkpoints[-1].gap:+.2f}")
    model_col.metric("Scorer", trend.model_version)
    st.write(trend.explanation)

    if trend.checkpoints:
        import pandas as pd

        st.markdown(
            "**How to read this:** the top chart compares performance with help "
            "(assisted) against performance alone (unassisted) at each weekly "
            "checkpoint. The bottom chart is their difference. A rising gap means "
            "growing reliance on assistance; a falling gap means independent skill "
            "is catching up; a flat gap means the two move together."
        )
        labels = [c.checkpoint_id for c in trend.checkpoints]
        series = pd.DataFrame(
            {
                "assisted": [c.assisted_score for c in trend.checkpoints],
                "unassisted": [c.unassisted_score for c in trend.checkpoints],
            },
            index=labels,
        )
        st.markdown("**Assisted vs unassisted performance**")
        st.line_chart(series)
        st.markdown("**Gap (assisted - unassisted)**")
        st.line_chart(pd.DataFrame({"gap": [c.gap for c in trend.checkpoints]}, index=labels))

        rows = []
        previous = None
        for c in trend.checkpoints:
            change = None if previous is None else c.gap - previous
            rows.append(
                {
                    "checkpoint": c.checkpoint_id,
                    "assisted": c.assisted_score,
                    "unassisted": c.unassisted_score,
                    "gap": c.gap,
                    "gap change": "" if change is None else f"{change:+.2f}",
                    "evidence": ", ".join(c.evidence_attempt_ids),
                }
            )
            previous = c.gap
        st.dataframe(rows, use_container_width=True)

    st.subheader("Misconceptions and interventions")
    if not result.clusters:
        st.write("No recurring misconception clusters found in the stored evidence.")
    for cluster, plan in zip(result.clusters, result.remediation):
        with st.expander(f"{cluster.cluster_id}: {cluster.concept_summary}"):
            st.write(f"Evidence: {', '.join(cluster.evidence_attempt_ids)}")
            st.write(f"Plan status: {plan.status}")
            if plan.teacher_summary:
                st.write(plan.teacher_summary)

    with st.expander("What the student sees"):
        st.write(result.explanation.headline)
        st.write(result.explanation.plain_language)

    summary = "\n\n".join(
        [
            f"Student: {student_id}",
            f"Skill: {skill_id}",
            f"Trend: {trend.status}",
            f"Verifier: {verification.verdict} ({verification.confidence} confidence)",
            f"Verifier reasons: {'; '.join(verification.reasons)}",
            f"Evidence: {'; '.join(result.explanation.evidence_points)}",
            f"Remediation: {'; '.join(p.teacher_summary for p in result.remediation) or 'None'}",
        ]
    )
    st.download_button(
        "Download student summary",
        summary,
        file_name=f"{student_id}-{skill_id}-summary.txt",
        mime="text/plain",
    )
