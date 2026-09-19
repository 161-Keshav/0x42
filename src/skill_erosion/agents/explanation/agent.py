"""Student-facing agent: explains a flag back to the student in plain language.

Uses only the student's own scoped data (trend, verification, top cluster).
Never exposes other students or raw rubric internals.
"""

from typing import Mapping

from skill_erosion.contracts.models import (
    CheckpointScore,
    FlagExplanation,
    FlagVerification,
    MisconceptionCluster,
    TrendReport,
)
from skill_erosion.logging_utils import get_logger, timed_agent

logger = get_logger("explanation")

_HEADLINES = {
    "widening": "Your independent work is drifting away from your assisted work",
    "narrowing": "Your independent work is catching up to your assisted work",
    "stable": "Your assisted and independent work are moving together",
    "contradictory": "Your recent results are mixed, so nothing is certain yet",
    "insufficient_data": "Not enough check-ins yet to say anything definite",
}


def _coerce_trend(raw: TrendReport | Mapping) -> TrendReport:
    if isinstance(raw, TrendReport):
        return raw
    data = dict(raw)
    data["checkpoints"] = [
        c if isinstance(c, CheckpointScore) else CheckpointScore(**c)
        for c in data["checkpoints"]
    ]
    return TrendReport(**data)


def _coerce_verification(raw: FlagVerification | Mapping) -> FlagVerification:
    return raw if isinstance(raw, FlagVerification) else FlagVerification(**dict(raw))


def _coerce_cluster(raw: MisconceptionCluster | Mapping | None) -> MisconceptionCluster | None:
    if raw is None or isinstance(raw, MisconceptionCluster):
        return raw
    return MisconceptionCluster(**dict(raw))


@timed_agent(logger, "explanation")
def explain_flag(
    trend: TrendReport | Mapping,
    verification: FlagVerification | Mapping,
    cluster: MisconceptionCluster | Mapping | None = None,
) -> FlagExplanation:
    """Explain a student's own flag in plain language using their own data."""
    trend = _coerce_trend(trend)
    verification = _coerce_verification(verification)
    cluster = _coerce_cluster(cluster)

    headline = _HEADLINES[trend.status]
    evidence = [
        f"{c.checkpoint_id}: your assisted score was {c.assisted_score:.2f}; "
        f"your unassisted score was {c.unassisted_score:.2f}; "
        f"the difference was {c.gap:+.2f}"
        for c in trend.checkpoints
    ]
    if not trend.checkpoints:
        plain = (
            "There are no scored check-ins for this skill yet. "
            "Complete the weekly tasks and this page will update."
        )
    else:
        first, last = trend.checkpoints[0], trend.checkpoints[-1]
        plain = (
            f"Across {len(trend.checkpoints)} check-ins, your unassisted score moved "
            f"from {first.unassisted_score:.2f} to {last.unassisted_score:.2f}, while "
            f"your assisted score moved from {first.assisted_score:.2f} to "
            f"{last.assisted_score:.2f}. The gap changed from {first.gap:+.2f} to "
            f"{last.gap:+.2f}. "
            f"The system reads this as '{trend.status.replace('_', ' ')}' and a reviewer "
            f"{'confirmed it' if verification.verdict == 'confirmed' else 'marked it as uncertain'} "
            f"({verification.confidence} confidence)."
        )
    if trend.status == "insufficient_data":
        next_step = "Finish the next weekly checkpoint so a fair comparison becomes possible."
    elif cluster is not None:
        next_step = f"Practice next: {cluster.concept_summary}. Your targeted exercise is below."
    else:
        next_step = "Keep completing the weekly unassisted checkpoints."
    logger.info("explained %s/%s -> %s", trend.student_id, trend.skill_id, headline)
    return FlagExplanation(
        student_id=trend.student_id,
        skill_id=trend.skill_id,
        headline=headline,
        plain_language=plain,
        evidence_points=evidence,
        next_step=next_step,
    )
