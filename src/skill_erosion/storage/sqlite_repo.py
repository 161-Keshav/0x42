"""Append-only versions; every batch is one SQLite transaction."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from skill_erosion.contracts.models import Attempt, IngestionResult, CheckInTrace

class SQLiteRepository:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS attempts (
                  attempt_id TEXT NOT NULL, version INTEGER NOT NULL,
                  student_id TEXT NOT NULL, skill_id TEXT NOT NULL, payload TEXT NOT NULL,
                  PRIMARY KEY(attempt_id,version));
                CREATE INDEX IF NOT EXISTS attempts_scope ON attempts(student_id,skill_id);
                CREATE TABLE IF NOT EXISTS decisions (
                  student_id TEXT, skill_id TEXT, decision TEXT CHECK(decision IN ('intervene','monitor','dismiss')),
                  updated_at TEXT, PRIMARY KEY(student_id,skill_id));
                CREATE TABLE IF NOT EXISTS parent_links (
                  parent_account_id TEXT PRIMARY KEY, student_id TEXT UNIQUE NOT NULL);
                CREATE TABLE IF NOT EXISTS analyses (
                  analysis_id TEXT PRIMARY KEY, student_id TEXT, skill_id TEXT, created_at TEXT, payload TEXT);
                CREATE TABLE IF NOT EXISTS checkins (
                  trace_id TEXT PRIMARY KEY, student_id TEXT, skill_id TEXT, timestamp TEXT,
                  origin TEXT DEFAULT 'student_initiated');
            """)
    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db: yield db
        finally: db.close()
    def store(self, attempts):
        stored=0
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            for a in sorted(attempts, key=lambda a:(a.attempt_id,a.version)):
                payload=a.model_dump_json()
                exact=db.execute("SELECT payload FROM attempts WHERE attempt_id=? AND version=?",(a.attempt_id,a.version)).fetchone()
                if exact:
                    if exact["payload"] != payload: raise ValueError(f"Conflicting version: {a.evidence_id}")
                    continue
                latest=db.execute("SELECT payload FROM attempts WHERE attempt_id=? ORDER BY version DESC LIMIT 1",(a.attempt_id,)).fetchone()
                if latest:
                    prior=Attempt.model_validate_json(latest["payload"])
                    immutable=("student_id","skill_id","task_id","checkpoint_id","matched_task_set_id","assistance","origin")
                    if any(getattr(a,k)!=getattr(prior,k) for k in immutable): raise ValueError("Cannot change attempt identity or scope")
                    expected=prior.version+1
                else: expected=1
                if a.version != expected: raise ValueError(f"Expected version {expected} for {a.attempt_id}")
                db.execute("INSERT INTO attempts VALUES(?,?,?,?,?)",(a.attempt_id,a.version,a.student_id,a.skill_id,payload))
                stored+=1
        return IngestionResult(attempt_ids=list(dict.fromkeys(a.attempt_id for a in attempts)), stored_versions=stored)
    def history(self, student_id, skill_id=None):
        sql="""SELECT a.payload FROM attempts a WHERE a.student_id=? AND
          a.version=(SELECT MAX(b.version) FROM attempts b WHERE b.attempt_id=a.attempt_id)"""
        params=[student_id]
        if skill_id is not None: sql+=" AND a.skill_id=?"; params.append(skill_id)
        with self.connection() as db: rows=db.execute(sql,params).fetchall()
        return sorted([Attempt.model_validate_json(r["payload"]) for r in rows],key=lambda a:(a.timestamp,a.attempt_id))
    def count_versions(self):
        with self.connection() as db: return db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
    def students(self):
        with self.connection() as db: return [r[0] for r in db.execute("SELECT DISTINCT student_id FROM attempts ORDER BY student_id")]
    def set_decision(self, student_id, skill_id, decision):
        if decision not in ("intervene","monitor","dismiss"): raise ValueError("Invalid teacher decision")
        with self.connection() as db:
            db.execute("INSERT INTO decisions VALUES(?,?,?,?) ON CONFLICT(student_id,skill_id) DO UPDATE SET decision=excluded.decision,updated_at=excluded.updated_at",(student_id,skill_id,decision,datetime.now(timezone.utc).isoformat()))
    def get_decision(self, student_id, skill_id):
        with self.connection() as db:
            r=db.execute("SELECT decision FROM decisions WHERE student_id=? AND skill_id=?",(student_id,skill_id)).fetchone()
        return r[0] if r else None
    def link_parent(self, parent_account_id, student_id):
        if student_id not in self.students(): raise ValueError("Unknown student")
        with self.connection() as db:
            row=db.execute("SELECT student_id FROM parent_links WHERE parent_account_id=?",(parent_account_id,)).fetchone()
            if row:
                if row[0]!=student_id: raise ValueError("Parent account already linked")
                return
            try: db.execute("INSERT INTO parent_links VALUES(?,?)",(parent_account_id,student_id))
            except sqlite3.IntegrityError as e: raise ValueError("Student already linked") from e
    def get_linked_student(self, parent_account_id):
        with self.connection() as db:
            r=db.execute("SELECT student_id FROM parent_links WHERE parent_account_id=?",(parent_account_id,)).fetchone()
        if not r: raise PermissionError("Parent account has no linked student")
        return r[0]
    def history_for_parent(self, parent_account_id, requested_student_id=None):
        linked=self.get_linked_student(parent_account_id)
        if requested_student_id is not None and requested_student_id!=linked: raise PermissionError("Student is outside this parent account")
        return self.history(linked)
    def parent_accounts(self):
        with self.connection() as db: return [r[0] for r in db.execute("SELECT parent_account_id FROM parent_links ORDER BY parent_account_id")]
    def save_analysis(self, journey):
        with self.connection() as db:
            db.execute("INSERT INTO analyses VALUES(?,?,?,?,?)",(uuid4().hex,journey.trend.student_id,journey.trend.skill_id,datetime.now(timezone.utc).isoformat(),journey.model_dump_json()))
    def request_checkin(self, student_id, skill_id):
        if not self.history(student_id,skill_id): raise ValueError("No assessment evidence for this student and skill")
        trace=CheckInTrace(trace_id=uuid4().hex,student_id=student_id,skill_id=skill_id,timestamp=datetime.now(timezone.utc).isoformat())
        with self.connection() as db:
            db.execute("INSERT INTO checkins VALUES(?,?,?,?,?)",tuple(trace.model_dump().values()))
        return trace
    def checkin_queue(self):
        with self.connection() as db: rows=db.execute("SELECT * FROM checkins WHERE origin='student_initiated' ORDER BY timestamp DESC").fetchall()
        return [dict(r) for r in rows]
    def versions(self, student_id, skill_id):
        with self.connection() as db:
            rows=db.execute("SELECT payload FROM attempts WHERE student_id=? AND skill_id=? ORDER BY attempt_id,version",(student_id,skill_id)).fetchall()
        return [Attempt.model_validate_json(r[0]) for r in rows]
