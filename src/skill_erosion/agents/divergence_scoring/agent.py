"""Divergence scorer: matched checkpoint pairs and an auditable gap trend.

Performance per attempt blends correctness (60%), time efficiency (40%), and a
hint penalty. Conditions are only compared within the same matched task set,
checkpoint, and rubric version. Fewer than three paired checkpoints yields
`insufficient_data`; non-monotonic movement yields `contradictory`.
"""

from collections import defaultdict

from skill_erosion.contracts.models import Attempt, CheckpointScore, TrendReport, TrendStatus
from skill_erosion.logging_utils import get_logger, timed_agent
from skill_erosion.storage import default_repository

logger = get_logger("divergence_scoring")

MODEL_VERSION = "gap-ensemble-v1"
_MIN_PAIRED_CHECKPOINTS = 3
_STABLE_TOLERANCE = 0.02
_TIME_BASELINE_SECONDS = 600
_HINT_PENALTY = 0.05


def _performance(attempt: Attempt) -> float:
    time_score = max(0.0, 1.0 - attempt.time_taken_seconds / _TIME_BASELINE_SECONDS)
    penalty = min(0.15, _HINT_PENALTY * attempt.hint_count)
    score = 0.6 * attempt.correctness + 0.4 * time_score - penalty
    return round(min(1.0, max(0.0, score)), 4)


def _paired_checkpoints(history: list[Attempt]) -> list[CheckpointScore]:
    groups: dict[tuple[str, str, str], dict[str, Attempt]] = defaultdict(dict)
    for attempt in history:
        key = (attempt.checkpoint_id, attempt.matched_task_set_id, attempt.rubric_version)
        existing = groups[key].get(attempt.assistance)
        if existing is None or attempt.version > existing.version:
            groups[key][attempt.assistance] = attempt
    checkpoints: list[CheckpointScore] = []
    for (checkpoint_id, _, _), pair in groups.items():
        if set(pair) != {"assisted", "unassisted"}:
            continue
        assisted, unassisted = pair["assisted"], pair["unassisted"]
        assisted_score = _performance(assisted)
        unassisted_score = _performance(unassisted)
        checkpoints.append(
            CheckpointScore(
                checkpoint_id=checkpoint_id,
                timestamp=max(assisted.timestamp, unassisted.timestamp),
                assisted_score=assisted_score,
                unassisted_score=unassisted_score,
                gap=round(assisted_score - unassisted_score, 4),
                evidence_attempt_ids=[
                    f"{assisted.attempt_id}:v{assisted.version}",
                    f"{unassisted.attempt_id}:v{unassisted.version}",
                ],
            )
        )
    checkpoints.sort(key=lambda c: (c.timestamp, c.checkpoint_id))
    return checkpoints


def _classify(gaps: list[float]) -> TrendStatus:
    if len(gaps) < _MIN_PAIRED_CHECKPOINTS:
        return "insufficient_data"
    deltas = [b - a for a, b in zip(gaps, gaps[1:])]
    if all(abs(d) <= _STABLE_TOLERANCE for d in deltas):
        return "stable"
    if all(d > _STABLE_TOLERANCE for d in deltas):
        return "widening"
    if all(d < -_STABLE_TOLERANCE for d in deltas):
        return "narrowing"
    return "contradictory"


@timed_agent(logger, "divergence_scoring")
def score_divergence(student_id: str, skill_id: str) -> TrendReport:
    """Score the assisted/unassisted gap across matched, ordered checkpoints."""
    history = default_repository().history(student_id, skill_id)
    checkpoints = _paired_checkpoints(history)
    status = _classify([c.gap for c in checkpoints])
    if not checkpoints:
        explanation = f"No stored matched attempts for {student_id} on {skill_id}."
    elif status == "insufficient_data":
        explanation = (
            f"Only {len(checkpoints)} paired checkpoint(s); "
            f"{_MIN_PAIRED_CHECKPOINTS} are required before assigning a trend."
        )
    else:
        gaps = ", ".join(f"{c.checkpoint_id}={c.gap:+.2f}" for c in checkpoints)
        explanation = f"Gap {status} across {len(checkpoints)} paired checkpoints ({gaps})."
    logger.info("scored %s/%s -> %s over %d checkpoints", student_id, skill_id, status, len(checkpoints))
    return TrendReport(
        student_id=student_id,
        skill_id=skill_id,
        status=status,
        checkpoints=checkpoints,
        model_version=MODEL_VERSION,
        explanation=explanation,
    )
