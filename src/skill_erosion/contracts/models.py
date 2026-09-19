"""Initial contracts, not runtime validators. See docs/data-contract.md."""

from dataclasses import dataclass
from typing import Literal

Assistance = Literal["assisted", "unassisted"]
TrendStatus = Literal[
    "widening", "stable", "narrowing", "insufficient_data", "contradictory"
]


@dataclass(frozen=True)
class Attempt:
    attempt_id: str
    version: int
    student_id: str
    skill_id: str
    task_id: str
    matched_task_set_id: str
    checkpoint_id: str
    timestamp: str
    assistance: Assistance
    task_type: Literal["code", "written", "quiz"]
    response_text: str
    correctness: float
    time_taken_seconds: int
    hint_count: int
    rubric_version: str
    synthetic: bool
    similarity_to_prior: float | None = None
    origin: Literal["system", "student_initiated", "follow_up"] = "system"


@dataclass(frozen=True)
class IngestionResult:
    attempt_ids: list[str]
    stored_versions: int


@dataclass(frozen=True)
class CheckpointScore:
    checkpoint_id: str
    timestamp: str
    assisted_score: float
    unassisted_score: float
    gap: float
    evidence_attempt_ids: list[str]


@dataclass(frozen=True)
class TrendReport:
    student_id: str
    skill_id: str
    status: TrendStatus
    checkpoints: list[CheckpointScore]
    model_version: str
    explanation: str


@dataclass(frozen=True)
class MisconceptionCluster:
    cluster_id: str
    student_id: str
    skill_id: str
    concept_summary: str
    evidence_attempt_ids: list[str]
    embedding_model_version: str


@dataclass(frozen=True)
class RemediationPlan:
    student_id: str
    skill_id: str
    cluster_id: str
    teacher_summary: str
    student_exercise: str
    resource_ids: list[str]
    status: Literal["ready", "no_matching_resource", "insufficient_evidence"]


@dataclass(frozen=True)
class FlagVerification:
    student_id: str
    skill_id: str
    trend_status: TrendStatus
    verdict: Literal["confirmed", "downgraded"]
    confidence: Literal["high", "medium", "low"]
    reasons: list[str]
    model_version: str


@dataclass(frozen=True)
class FlagExplanation:
    student_id: str
    skill_id: str
    headline: str
    plain_language: str
    evidence_points: list[str]
    next_step: str


@dataclass(frozen=True)
class JourneyResult:
    trend: TrendReport
    verification: FlagVerification
    clusters: list[MisconceptionCluster]
    remediation: list[RemediationPlan]
    explanation: FlagExplanation
