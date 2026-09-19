from typing import Protocol

from skill_erosion.contracts.models import Attempt


class TraceRepository(Protocol):
    def append(self, attempt: Attempt) -> None:
        """Immutable (attempt_id, version); identical reimports are no-ops."""
        ...

    def history(self, student_id: str, skill_id: str) -> list[Attempt]:
        """Latest version per attempt, sorted by UTC timestamp; no cross-student data."""
        ...

    def set_teacher_decision(
        self, student_id: str, skill_id: str, decision: str
    ) -> None:
        ...

    def get_teacher_decision(self, student_id: str, skill_id: str) -> str | None:
        ...


class EmbeddingIndex(Protocol):
    def upsert(self, attempt: Attempt, vector: list[float], model_version: str) -> None:
        """Key by attempt ID, version and embedding model; persist matching metadata."""
        ...

    def query(
        self, vector: list[float], student_id: str, skill_id: str, limit: int
    ) -> list[tuple[str, float]]:
        """Return versioned attempt keys with similarity, scoped to student and skill."""
        ...
