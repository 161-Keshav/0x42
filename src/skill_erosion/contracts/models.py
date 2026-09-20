"""Versioned, JSON-safe boundaries between the independent agents."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Assistance = Literal["assisted", "unassisted"]
TrendStatus = Literal["widening", "stable", "narrowing", "insufficient_data", "contradictory"]
Decision = Literal["intervene", "monitor", "dismiss"]

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

class Attempt(Contract):
    attempt_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    student_id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    matched_task_set_id: str = Field(min_length=1)
    checkpoint_id: str = Field(min_length=1)
    timestamp: str
    assistance: Assistance
    task_type: Literal["code", "written", "quiz"]
    response_text: str
    correctness: float = Field(ge=0, le=1)
    time_taken_seconds: int = Field(ge=0)
    hint_count: int = Field(ge=0)
    rubric_version: str = Field(min_length=1)
    synthetic: bool
    similarity_to_prior: float | None = Field(default=None, ge=-1, le=1)
    origin: Literal["system", "student_initiated", "follow_up"] = "system"
    self_reported_confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("timestamp")
    @classmethod
    def iso_timestamp(cls, value):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None: raise ValueError("Timestamp must include a timezone")
        return dt.astimezone(timezone.utc).isoformat()

    @field_validator("attempt_id", "student_id", "skill_id", "task_id", "matched_task_set_id", "checkpoint_id", "rubric_version")
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError("Identifier cannot be blank")
        return value

    @property
    def evidence_id(self): return f"{self.attempt_id}@v{self.version}"

class IngestionResult(Contract):
    attempt_ids: list[str]
    stored_versions: int

class CheckpointScore(Contract):
    checkpoint_id: str
    timestamp: str
    assisted_score: float
    unassisted_score: float
    gap: float
    evidence_attempt_ids: list[str]

class TrendReport(Contract):
    student_id: str
    skill_id: str
    status: TrendStatus
    checkpoints: list[CheckpointScore]
    model_version: str
    explanation: str

class FlagVerification(Contract):
    verdict: Literal["confirmed", "downgraded"]
    confidence: Literal["low", "medium", "high"]
    trend_status: TrendStatus
    reasons: list[str]
    verifier_model_version: str

class MisconceptionCluster(Contract):
    student_id: str
    skill_id: str
    concept_summary: str
    evidence_attempt_ids: list[str]
    embedding_model_version: str

class RemediationPlan(Contract):
    status: Literal["ready", "no_matching_resource", "insufficient_evidence"]
    teacher_summary: str | None = None
    student_exercise: str | None = None
    resource_ids: list[str] = Field(default_factory=list)

class FlagExplanation(Contract):
    headline: str
    explanation: str
    evidence_points: list[str]
    next_step: str

class JourneyResult(Contract):
    trend: TrendReport
    verification: FlagVerification
    clusters: list[MisconceptionCluster]
    remediation: list[RemediationPlan]
    explanation: FlagExplanation

class Resource(Contract):
    resource_id: str
    title: str
    description: str
    teacher_summary: str
    student_exercise: str
    path: str

class CheckInTrace(Contract):
    trace_id: str
    student_id: str
    skill_id: str
    timestamp: str
    origin: Literal["student_initiated"] = "student_initiated"
