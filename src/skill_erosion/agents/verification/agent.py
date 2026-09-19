"""Verifier agent: decides whether a trend flag is signal or noise.

Sits between the divergence scorer and the human review. Rule checks cover
rushed unassisted attempts, thin checkpoint counts, fluke-sized gap movement,
and contradictory direction. Output is a confirmed/downgraded verdict with a
confidence label and auditable reasons.
"""

from typing import Mapping

from skill_erosion.contracts.models import (
    CheckpointScore,
    FlagVerification,
    TrendReport,
)
from skill_erosion.logging_utils import get_logger, timed_agent
from skill_erosion.storage import default_repository

logger = get_logger("verification")
VERIFY_VERSION = "flag-verifier-v1"
_RUSH_SECONDS = 60
_NOISE_BAND = 0.08
_CONFIDENT_CHECKPOINTS = 4


def _coerce_trend(raw: TrendReport | Mapping) -> TrendReport:
    if isinstance(raw, TrendReport):
        return raw
    data = dict(raw)
    data["checkpoints"] = [
        c if isinstance(c, CheckpointScore) else CheckpointScore(**c)
        for c in data["checkpoints"]
    ]
    return TrendReport(**data)


def _rushed_unassisted(trend: TrendReport) -> list[str]:
    repo = default_repository()
    rushed: list[str] = []
    for checkpoint in trend.checkpoints:
        for key in checkpoint.evidence_attempt_ids:
            attempt_id, _, version = key.rpartition(":v")
            if not version.isdigit():
                continue
            attempt = repo.get(attempt_id, int(version))
            if (
                attempt is not None
                and attempt.assistance == "unassisted"
                and attempt.time_taken_seconds < _RUSH_SECONDS
            ):
                rushed.append(key)
    return rushed


@timed_agent(logger, "verification")
def verify_flag(trend: TrendReport | Mapping) -> FlagVerification:
    """Confirm a flag with a confidence label, or downgrade it as noise."""
    trend = _coerce_trend(trend)
    checkpoints = trend.checkpoints
    base: dict[str, str] = {
        "student_id": trend.student_id,
        "skill_id": trend.skill_id,
        "model_version": VERIFY_VERSION,
    }
    if trend.status == "insufficient_data":
        return FlagVerification(
            verdict="downgraded",
            confidence="low",
            reasons=[
                f"Only {len(checkpoints)} paired checkpoint(s) behind this flag; "
                "a single data point cannot establish a pattern."
            ],
            trend_status=trend.status,
            **base,
        )
    if trend.status == "contradictory":
        return FlagVerification(
            verdict="downgraded",
            confidence="medium",
            reasons=["Gap direction flips between checkpoints; treat as noise until it resolves."],
            trend_status=trend.status,
            **base,
        )

    verdict = "confirmed"
    reasons: list[str] = []
    rushed = _rushed_unassisted(trend)
    if rushed:
        verdict = "downgraded"
        reasons.append(
            f"{len(rushed)} unassisted attempt(s) finished in under {_RUSH_SECONDS}s; "
            "scores may reflect disengagement, not skill."
        )
    gaps = [c.gap for c in checkpoints]
    movement = abs(gaps[-1] - gaps[0])
    if trend.status in ("widening", "narrowing") and movement < _NOISE_BAND:
        verdict = "downgraded"
        reasons.append(
            f"Total gap movement {movement:.2f} is within the {_NOISE_BAND:.2f} noise band; likely a fluke."
        )
    if verdict == "confirmed":
        if trend.status == "stable":
            reasons.append(f"Gap steady within tolerance across {len(checkpoints)} checkpoints; no erosion signal.")
        else:
            reasons.append(
                f"Consistent {trend.status} movement ({gaps[0]:+.2f} -> {gaps[-1]:+.2f}) "
                f"across {len(checkpoints)} paired checkpoints."
            )
    confidence = "high" if len(checkpoints) >= _CONFIDENT_CHECKPOINTS else "medium"
    if verdict == "downgraded":
        confidence = "low" if not reasons else confidence
    logger.info("verified %s/%s -> %s (%s)", base["student_id"], base["skill_id"], verdict, confidence)
    return FlagVerification(
        verdict=verdict,
        confidence=confidence,
        reasons=reasons,
        trend_status=trend.status,
        **base,
    )
