# Data contract and interpretation

`src/skill_erosion/contracts/models.py` defines the agent boundaries with Pydantic, finite bounded scores and confidence, explicit assistance conditions, timezone-normalized ISO timestamps, versioned identities and forbidden extra fields. JSON and CSV both pass through the same validation path.

Attempts are append-only. A new ID starts at version 1; revisions must be consecutive and keep student, skill, task, matched set, checkpoint, assistance and origin unchanged. Identical versions are a no-op; a conflicting batch rolls back atomically. Evidence uses `attempt_id@vN`; only the latest version contributes to analysis.

Pair by checkpoint, matched task set and rubric. Average repetitions within each condition, then weight matched sets equally. Incomplete pairs are excluded. Fewer than two paired checkpoints means insufficient data. Adjacent gap changes within 0.03 are stable; a strict majority beyond that threshold plus matching net direction gives widening/narrowing. Remaining histories are contradictory. The verifier additionally requires three checkpoints across at least fourteen days for strong evidence.

Student-requested check-ins are ungraded `CheckInTrace` events with `origin=student_initiated`. They enter the teacher queue without inventing an assessment score. Follow-up quiz answers are graded attempts; unpaired independent follow-ups do not create invented assisted scores.

The parent repository boundary resolves the linked student server-side and rejects attempts to request another student. Account selectors are local demonstration identities. Deployments with real students require authenticated sessions and per-role authorization outside this demo.
