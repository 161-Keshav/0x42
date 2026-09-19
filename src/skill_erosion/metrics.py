"""Education-quality metrics derived from the scoped attempt history."""

from collections import Counter
from datetime import datetime
import json

from skill_erosion.contracts.models import Attempt
from skill_erosion.config import taxonomy_path


def _days_between(first: str, last: str) -> float:
    start = datetime.fromisoformat(first.replace("Z", "+00:00"))
    end = datetime.fromisoformat(last.replace("Z", "+00:00"))
    return max(0.0, (end - start).total_seconds() / 86400)


def calculate_metrics(
    attempts: list[Attempt],
    related_skill_id: str | None = None,
    related_skill_attempts: list[Attempt] | None = None,
) -> dict[str, float | int | str | None]:
    """Return honest metrics; unavailable signals remain explicitly unavailable.

    ``attempts`` stays scoped to one student/skill, same as before, so every
    other metric here is unaffected by this change. Cross-skill transfer is
    the one metric that inherently needs a second skill's evidence to mean
    anything, so it takes its own optional ``related_skill_attempts`` list
    rather than being computed from ``attempts`` alone, which would always
    show no evidence for the related skill.
    """
    unassisted = [a for a in attempts if a.assistance == "unassisted"]
    followups = [a for a in attempts if a.origin == "follow_up"]
    hint_attempts = [a for a in attempts if a.hint_count > 0]
    errors = [a.response_text.strip().lower() for a in unassisted if a.correctness < 0.5]
    error_counts = Counter(errors)
    repeated_error_ratio = (
        max(error_counts.values()) / len(errors) if errors else None
    )
    retention_decay = None
    if len(followups) >= 2:
        first, last = followups[0], followups[-1]
        retention_decay = first.correctness - last.correctness

    source_skill_id = attempts[0].skill_id if attempts else None
    transfer_status = "insufficient_data"
    if source_skill_id and related_skill_id and related_skill_attempts:
        transfer_status = cross_skill_transfer(
            list(attempts) + list(related_skill_attempts),
            source_skill_id,
            related_skill_id,
        )

    return {
        "hint_dependency_ratio": (
            len(hint_attempts) / len(attempts) if attempts else 0.0
        ),
        "retention_decay": retention_decay,
        "error_pattern_diversity": (
            len(error_counts) / len(errors) if errors else None
        ),
        "repeated_error_ratio": repeated_error_ratio,
        "unassisted_attempts": len(unassisted),
        "follow_up_attempts": len(followups),
        "observed_span_days": (
            _days_between(attempts[0].timestamp, attempts[-1].timestamp)
            if len(attempts) >= 2
            else 0.0
        ),
        "confidence_calibration": confidence_calibration(attempts),
        "cross_skill_transfer": transfer_status,
    }


def confidence_calibration(attempts: list[Attempt]) -> str:
    """Classify confidence against correctness for one student/skill scope."""
    observed = [
        a for a in attempts
        if a.self_reported_confidence is not None
    ]
    if len(observed) < 3:
        return "insufficient_data"
    bias = sum(
        a.self_reported_confidence - a.correctness
        for a in observed
    ) / len(observed)
    if bias > 0.15:
        return "overconfident"
    if bias < -0.15:
        return "underconfident"
    return "well_calibrated"


def cross_skill_transfer(
    attempts: list[Attempt],
    source_skill: str,
    target_skill: str,
    related_skills: dict[str, list[str]] | None = None,
    direct_practice_skills: set[str] | None = None,
) -> str:
    """Detect improvement on a related target skill without direct target practice."""
    if related_skills is None:
        taxonomy = json.loads(taxonomy_path().read_text(encoding="utf-8"))
        relations = {
            item["skill_id"]: item.get("related_skills", [])
            for item in taxonomy["skills"]
        }
    else:
        relations = related_skills
    if target_skill not in relations.get(source_skill, []):
        return "insufficient_data"
    if target_skill in (direct_practice_skills or set()):
        return "insufficient_data"
    source = [a for a in attempts if a.skill_id == source_skill and a.assistance == "unassisted"]
    target = [a for a in attempts if a.skill_id == target_skill and a.assistance == "unassisted"]
    if len(source) < 2 or len(target) < 2:
        return "insufficient_data"
    source_improved = source[-1].correctness > source[0].correctness
    target_improved = target[-1].correctness > target[0].correctness
    return "transfer_detected" if source_improved and target_improved else "no_transfer_detected"
