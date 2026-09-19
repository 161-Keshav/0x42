"""Append-only SQLite trace repository with a derived embedding index.

Canonical attempts live in `attempts`; embeddings are derived state keyed by
versioned attempt key and encoder version, so they can be rebuilt at any time.
"""

import json
import sqlite3
import threading
from pathlib import Path

from skill_erosion.contracts.models import Attempt

_SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
    attempt_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    student_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (attempt_id, version)
);
CREATE INDEX IF NOT EXISTS idx_attempts_scope ON attempts (student_id, skill_id);
CREATE TABLE IF NOT EXISTS embeddings (
    attempt_key TEXT NOT NULL,
    model_version TEXT NOT NULL,
    vector TEXT NOT NULL,
    PRIMARY KEY (attempt_key, model_version)
);
CREATE TABLE IF NOT EXISTS teacher_decisions (
    student_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, skill_id)
);
CREATE TABLE IF NOT EXISTS parent_links (
    parent_account_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL UNIQUE
);
"""


class SQLiteTraceRepository:
    def __init__(self, path: Path) -> None:
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    @staticmethod
    def _payload(attempt: Attempt) -> str:
        return json.dumps(attempt.__dict__, sort_keys=True)

    @staticmethod
    def _payload_data(payload: str) -> dict:
        data = json.loads(payload)
        # `origin` was added after the initial fixture/database schema.
        # Treat old records as system-ingested attempts for idempotent reloads.
        data.setdefault("origin", "system")
        return data

    @classmethod
    def _payloads_equivalent(cls, stored: str, incoming: str) -> bool:
        stored_data = cls._payload_data(stored)
        incoming_data = cls._payload_data(incoming)
        # `self_reported_confidence` was added later and is optional. A legacy
        # row without it must remain reloadable without inventing confidence.
        if (
            "self_reported_confidence" not in stored_data
            or stored_data["self_reported_confidence"] is None
        ):
            stored_data.pop("self_reported_confidence", None)
            incoming_data.pop("self_reported_confidence", None)
        return stored_data == incoming_data

    def append(self, attempt: Attempt) -> None:
        payload = self._payload(attempt)
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT payload FROM attempts WHERE attempt_id=? AND version=?",
                (attempt.attempt_id, attempt.version),
            ).fetchone()
            if row is not None:
                if not self._payloads_equivalent(row["payload"], payload):
                    raise ValueError(
                        f"Conflicting payload for immutable ({attempt.attempt_id}, v{attempt.version})"
                    )
                return
            self._conn.execute(
                "INSERT INTO attempts VALUES (?,?,?,?,?,?,?)",
                (
                    attempt.attempt_id,
                    attempt.version,
                    attempt.student_id,
                    attempt.skill_id,
                    attempt.checkpoint_id,
                    attempt.timestamp,
                    payload,
                ),
            )

    def history(self, student_id: str, skill_id: str) -> list[Attempt]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT a.payload FROM attempts a
                JOIN (
                    SELECT attempt_id, MAX(version) AS v FROM attempts
                    WHERE student_id=? AND skill_id=? GROUP BY attempt_id
                ) latest ON latest.attempt_id=a.attempt_id AND latest.v=a.version
                ORDER BY a.timestamp, a.attempt_id
                """,
                (student_id, skill_id),
            ).fetchall()
        return [Attempt(**json.loads(row["payload"])) for row in rows]

    def all_history(self, student_id: str) -> list[Attempt]:
        """Return the latest version of every attempt for one student."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT a.payload FROM attempts a
                JOIN (
                    SELECT attempt_id, MAX(version) AS v FROM attempts
                    WHERE student_id=? GROUP BY attempt_id
                ) latest ON latest.attempt_id=a.attempt_id AND latest.v=a.version
                ORDER BY a.timestamp, a.attempt_id
                """,
                (student_id,),
            ).fetchall()
        return [Attempt(**json.loads(row["payload"])) for row in rows]

    def get(self, attempt_id: str, version: int) -> Attempt | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM attempts WHERE attempt_id=? AND version=?",
                (attempt_id, version),
            ).fetchone()
        return Attempt(**json.loads(row["payload"])) if row else None

    def set_teacher_decision(self, student_id: str, skill_id: str, decision: str) -> None:
        if decision not in {"intervene", "monitor", "dismiss"}:
            raise ValueError(f"Unsupported teacher decision: {decision}")
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO teacher_decisions (student_id, skill_id, decision)
                VALUES (?, ?, ?)
                ON CONFLICT(student_id, skill_id) DO UPDATE SET
                    decision=excluded.decision,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (student_id, skill_id, decision),
            )

    def get_teacher_decision(self, student_id: str, skill_id: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT decision FROM teacher_decisions WHERE student_id=? AND skill_id=?",
                (student_id, skill_id),
            ).fetchone()
        return row["decision"] if row else None

    def link_parent(self, parent_account_id: str, student_id: str) -> None:
        with self._lock, self._conn:
            existing = self._conn.execute(
                "SELECT student_id FROM parent_links WHERE parent_account_id=?",
                (parent_account_id,),
            ).fetchone()
            if existing is not None and existing["student_id"] != student_id:
                raise ValueError("Parent account is already linked to another student")
            other = self._conn.execute(
                "SELECT parent_account_id FROM parent_links WHERE student_id=?",
                (student_id,),
            ).fetchone()
            if other is not None and other["parent_account_id"] != parent_account_id:
                raise ValueError("Student is already linked to another parent account")
            self._conn.execute(
                "INSERT OR REPLACE INTO parent_links (parent_account_id, student_id) VALUES (?, ?)",
                (parent_account_id, student_id),
            )

    def get_linked_student(self, parent_account_id: str, requested_student_id: str | None = None) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT student_id FROM parent_links WHERE parent_account_id=?",
                (parent_account_id,),
            ).fetchone()
        if row is None:
            raise PermissionError("Parent account has no linked student")
        linked = row["student_id"]
        if requested_student_id is not None and requested_student_id != linked:
            raise PermissionError("Parent account cannot access this student")
        return linked

    def parent_accounts(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT parent_account_id FROM parent_links ORDER BY parent_account_id"
            ).fetchall()
        return [row["parent_account_id"] for row in rows]

    def embedding_keys(self, model_version: str) -> set[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT attempt_key FROM embeddings WHERE model_version=?", (model_version,)
            ).fetchall()
        return {row["attempt_key"] for row in rows}

    def upsert_embedding(self, attempt_key: str, model_version: str, vector: list[float]) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO embeddings VALUES (?,?,?)",
                (attempt_key, model_version, json.dumps(vector)),
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
