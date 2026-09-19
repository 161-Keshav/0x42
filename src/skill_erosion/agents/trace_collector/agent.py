"""Trace collector: strict validation, idempotent versioning, embedding index."""

import math
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timezone
from typing import Mapping

from skill_erosion.config import known_skill_ids
from skill_erosion.contracts.models import Attempt, IngestionResult
from skill_erosion.embeddings.local import HashingTextEncoder
from skill_erosion.logging_utils import get_logger, timed_agent
from skill_erosion.storage import default_repository

logger = get_logger("trace_collector")
_encoder = HashingTextEncoder()


def _normalize_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid ISO 8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate(attempt: Attempt) -> Attempt:
    if not isinstance(attempt, Attempt):
        raise TypeError(f"Expected Attempt, got {type(attempt).__name__}")
    for field in ("attempt_id", "student_id", "skill_id", "task_id", "matched_task_set_id",
                  "checkpoint_id", "rubric_version"):
        if not getattr(attempt, field) or not str(getattr(attempt, field)).strip():
            raise ValueError(f"{field} must be a non-empty string")
    if type(attempt.version) is not int or attempt.version < 1:
        raise ValueError("version must be a positive integer")
    if attempt.skill_id not in known_skill_ids():
        raise ValueError(f"Unknown skill_id: {attempt.skill_id}")
    if attempt.assistance not in ("assisted", "unassisted"):
        raise ValueError("assistance must be 'assisted' or 'unassisted'")
    if attempt.task_type not in ("code", "written", "quiz"):
        raise ValueError("task_type must be code, written, or quiz")
    if not isinstance(attempt.response_text, str) or not attempt.response_text.strip():
        raise ValueError("response_text must be non-empty")
    if not (isinstance(attempt.correctness, (int, float))
            and math.isfinite(attempt.correctness) and 0.0 <= attempt.correctness <= 1.0):
        raise ValueError("correctness must be a finite number in [0, 1]")
    for field in ("time_taken_seconds", "hint_count"):
        value = getattr(attempt, field)
        if type(value) is not int or value < 0:
            raise ValueError(f"{field} must be a nonnegative integer")
    if type(attempt.synthetic) is not bool:
        raise ValueError("synthetic must be a boolean")
    similarity = attempt.similarity_to_prior
    if similarity is not None and not (
        isinstance(similarity, (int, float)) and math.isfinite(similarity) and 0.0 <= similarity <= 1.0
    ):
        raise ValueError("similarity_to_prior must be null or in [0, 1]")
    confidence = attempt.self_reported_confidence
    if confidence is not None and not (
        isinstance(confidence, (int, float))
        and math.isfinite(confidence)
        and 0.0 <= confidence <= 1.0
    ):
        raise ValueError("self_reported_confidence must be null or in [0, 1]")
    return replace(attempt, timestamp=_normalize_timestamp(attempt.timestamp))


def _coerce(raw: Attempt | Mapping) -> Attempt:
    if isinstance(raw, Attempt):
        return raw
    if isinstance(raw, Mapping):
        return Attempt(**dict(raw))
    raise TypeError(f"Cannot ingest {type(raw).__name__}")


def _index_missing(attempts: Sequence[Attempt]) -> None:
    repo = default_repository()
    indexed = repo.embedding_keys(_encoder.model_version)
    pending = [a for a in attempts if f"{a.attempt_id}:v{a.version}" not in indexed]
    if not pending:
        return
    try:
        vectors = _encoder.encode([a.response_text for a in pending])
    except Exception:
        return
    for attempt, vector in zip(pending, vectors):
        repo.upsert_embedding(
            f"{attempt.attempt_id}:v{attempt.version}", _encoder.model_version, vector
        )


@timed_agent(logger, "trace_collector")
def collect_traces(attempts: Sequence[Attempt | Mapping]) -> IngestionResult:
    """Validate and persist versions, then index embeddings using stable version IDs."""
    if not attempts:
        raise ValueError("attempts must contain at least one record")
    validated = [_validate(_coerce(raw)) for raw in attempts]
    repo = default_repository()
    for attempt in validated:
        repo.append(attempt)
    _index_missing(validated)
    unique_ids = list(dict.fromkeys(a.attempt_id for a in validated))
    version_count = len({(a.attempt_id, a.version) for a in validated})
    logger.info("ingested %d attempts across %d versions", len(unique_ids), version_count)
    return IngestionResult(attempt_ids=unique_ids, stored_versions=version_count)
