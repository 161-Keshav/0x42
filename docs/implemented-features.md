# Implemented Features

This document describes the features currently implemented in the Skill
Erosion Tracker repository. The current implementation is a deterministic
synthetic-data MVP for demonstrating the full assisted-versus-unassisted
learning workflow.

## End-to-end pipeline

The implemented journey is:

```text
trace collector
    -> divergence scorer
    -> verifier
    -> misconception clusterer
    -> remediation agent
    -> student explanation
    -> teacher and student UIs
```

The pipeline is orchestrated by
`src/skill_erosion/orchestration/pipeline.py` through `run_journey`.
Agents communicate through typed contracts and do not call one another
directly.

## Implemented agents

### 1. Trace collector

Location: `src/skill_erosion/agents/trace_collector/agent.py`

- Validates incoming attempt records.
- Enforces required identity and task fields.
- Stores attempts in the versioned SQLite trace repository.
- Rejects invalid correctness values and conflicting versions.
- Makes repeated ingestion idempotent.
- Keeps attempts scoped by student and skill.
- Supports synthetic CSV and JSON fixture ingestion.

### 2. Divergence scorer

Location: `src/skill_erosion/agents/divergence_scoring/agent.py`

- Matches assisted and unassisted attempts by checkpoint and task set.
- Computes assisted performance, unassisted performance, and their gap.
- Produces a longitudinal trend report.
- Classifies trends as:
  - `widening`
  - `stable`
  - `narrowing`
  - `insufficient_data`
  - `contradictory`
- Returns evidence attempt IDs and a versioned scorer name.
- Does not fabricate a trend when no matching history exists.

### 3. Verifier agent

Location: `src/skill_erosion/agents/verification/agent.py`

- Checks whether a scored flag has enough evidence.
- Detects thin evidence, short histories, and contradictory movement.
- Confirms strong flags.
- Downgrades noisy or insufficient flags.
- Returns:
  - verdict
  - confidence
  - trend status
  - reasons
  - verifier model/version

### 4. Misconception clusterer

Location: `src/skill_erosion/agents/misconception_clustering/agent.py`

- Groups repeated unassisted evidence for a student and skill.
- Uses the local embedding implementation for deterministic clustering.
- Produces student- and skill-scoped misconception clusters.
- Includes versioned evidence attempt IDs.
- Avoids creating clusters from insufficient repeated evidence.

### 5. Remediation agent

Location: `src/skill_erosion/agents/remediation/agent.py`

- Matches a misconception cluster to the curated remediation catalog.
- Produces separate teacher and student outputs.
- Returns:
  - teacher summary
  - student exercise
  - resource IDs
  - remediation status
- Supports these statuses:
  - `ready`
  - `no_matching_resource`
  - `insufficient_evidence`

Curated resources are stored in:

```text
resources/remediation/catalog.json
resources/remediation/
```

### 6. Student explanation agent

Location: `src/skill_erosion/agents/explanation/agent.py`

- Explains a flag in plain language.
- Uses only the selected student's own trend, verification, and cluster data.
- Produces:
  - headline
  - plain-language explanation
  - evidence points
  - next step
- Does not expose raw response text or other students' data.

## Product enhancement features

The following controls are also implemented on top of the original MVP:

- Student evidence is shown as checkpoint-level assisted score, unassisted
  score, and gap values, both in the explanation text and in a table.
- Students can click **Something feels off - request a check-in**. This
  creates a trace tagged with `origin="student_initiated"` for teacher review.
- The student follow-up retest rotates through three loops questions instead
  of always presenting the same question.
- Students can select **This exercise did not help**. The remediation lookup
  retries while excluding the current resource and clearly reports when no
  alternative catalog item exists.
- Teachers can save an **Intervene**, **Monitor**, or **Dismiss** decision.
  Decisions are persisted in SQLite and affect the next journey: dismissed
  flags suppress remediation, while monitored flags remain visible without
  silently changing the underlying trend.
- Teachers can run a cohort roll-up showing each student's trend, verifier
  result, confidence, and counts grouped by skill and trend status.
- Teachers can download a plain-text student summary containing trend,
  verifier reasoning, concrete evidence, and remediation status.
- The teacher dashboard has a separate student-initiated check-in queue.
- `src/skill_erosion/metrics.py` reports hint-dependency ratio, retention
  decay, repeated-error ratio, and error-pattern diversity without inventing
  values when evidence is missing.
- Confidence calibration is calculated from optional self-reported confidence
  values and returns `well_calibrated`, `overconfident`, `underconfident`, or
  `insufficient_data`.
- Cross-skill transfer checks related-skill improvement without direct target
  practice and returns `transfer_detected`, `no_transfer_detected`, or
  `insufficient_data`. `calculate_metrics` now actually calls this (it
  previously hardcoded the result to `None` regardless of evidence); the
  teacher dashboard passes the related skill's own history alongside the
  scoped skill's history so the comparison has real evidence on both sides.

## Shared contracts and storage

Location: `src/skill_erosion/contracts/models.py`

The typed data contracts currently include:

- `Attempt`
- `IngestionResult`
- `CheckpointScore`
- `TrendReport`
- `FlagVerification`
- `MisconceptionCluster`
- `RemediationPlan`
- `FlagExplanation`
- `JourneyResult`

Storage features:

- SQLite-backed versioned attempt repository.
- Student/skill-scoped history queries.
- Version-aware attempt identity.
- Idempotent re-import behavior.
- Conflict rejection for incompatible versions.
- Chroma-backed local sentence embeddings for misconception and remediation
  retrieval. The trace collector still maintains its existing local derived
  embedding index for ingestion bookkeeping.

The default database is:

```text
data/processed/traces.sqlite3
```

The database location can be changed with `SKILL_EROSION_DB`.

## Teacher dashboard

Location: `apps/teacher_dashboard/app.py`

Run with:

```powershell
python -m streamlit run apps/teacher_dashboard/app.py --server.port 8501
```

Current features:

- Select a synthetic student.
- Load or refresh synthetic attempts.
- Run the complete journey.
- Display verifier status and confidence.
- Display verifier reasons.
- Display a suggested teacher update.
- Show toast notifications for:
  - ingestion
  - confirmed flags
  - downgraded flags
  - suggested next updates
  - failures
- Display trend status and latest gap.
- Display scorer version.
- Plot assisted and unassisted performance.
- Plot the assisted-minus-unassisted gap.
- Display checkpoint evidence in a table.
- Display misconception clusters.
- Display remediation plan status and teacher summary.
- Preview the explanation shown to the student.
- Show learning-quality signals including hint dependency, retention decay,
  error-pattern diversity, confidence calibration, and transfer status when
  the required evidence exists.
- Plot hint-dependency ratio per checkpoint alongside the existing gap
  chart, using the evidence attempts already attached to each checkpoint.
- Cohort roll-up now renders a bar chart of trend-status counts per skill
  (previously table-only), and a second bar chart of confidence-calibration
  categories across the cohort.

## Student portal

Location: `apps/student_portal/app.py`

Run with:

```powershell
python -m streamlit run apps/student_portal/app.py --server.port 8502
```

Current features:

- Select a synthetic learner.
- Load or refresh synthetic attempts.
- Request a personalized practice step.
- Display why the student is seeing the intervention.
- Display the student's own evidence points.
- Display the next step in plain language.
- Display a targeted exercise when remediation is available.
- Display the source remediation resource.
- Submit a short unassisted follow-up check.
- Record the follow-up as a new checkpoint.
- Re-run the journey after the follow-up.
- Show whether the independent score moved and whether the gap narrowed.
- Show toast notifications for data loading, plan creation, follow-up results,
  and failures.

## Parent portal

Location: `apps/parent_portal/app.py`

Run with:

```powershell
python -m streamlit run apps/parent_portal/app.py --server.port 8503
```

The local demo maps each parent account to exactly one synthetic learner and
provides supportive, trend-oriented progress updates. Viewing an update
automatically loads the synthetic fixture when the selected learner has no
history, while the refresh button can reload it explicitly. Load and analysis
errors are shown in the UI and written to `data/logs/parent_portal.log`.
Parent accounts are stored in the SQLite `parent_links` table and the portal
loads only the linked learner; there is no learner dropdown. The question box
calls `src/skill_erosion/agents/parent_chat/agent.py`, which answers from the
linked learner's scoped journey data and retrieves the most relevant
teacher-curated resource through the local Chroma collection rather than
returning a static template. The chatbot does not retrieve data for any other
student.
It intentionally omits raw scores, verifier confidence, misconception labels,
peer comparisons, and accusatory language. Production authentication and
parent-to-student linking are not implemented yet.

## Follow-up retest loop

The student portal includes a basic closing-the-loop workflow:

1. The system identifies a possible skill gap.
2. The student receives a targeted exercise.
3. The student submits a short unassisted follow-up.
4. The follow-up is stored as a new attempt.
5. The journey is recalculated.
6. The UI reports whether the independent score improved.

The current follow-up question is a deterministic Python `range` quiz used for
the synthetic loops demo.

## Logging

Location: `src/skill_erosion/logging_utils.py`

Logging features:

- Shared privacy-safe log:
  `data/logs/skill_erosion.log`
- Teacher dashboard log:
  `data/logs/teacher_dashboard.log`
- Student portal log:
  `data/logs/student_portal.log`
- Automatic log-directory creation.
- Configurable log level through `SKILL_EROSION_LOG_LEVEL`.
- Configurable shared log path through `SKILL_EROSION_LOG`.
- Raw response text and tool arguments are not logged by default.
- Exceptions from the UIs are logged with stack traces while the UI shows a
  user-facing error message and toast.

Log files are ignored by Git except for the directory placeholder.

## MCP support

Location: `src/skill_erosion/mcp_server.py`

The following six tools are independently callable through FastMCP:

1. `collect_traces`
2. `score_divergence`
3. `verify_flag`
4. `cluster_misconceptions`
5. `recommend_remediation`
6. `explain_flag`

The orchestrator supports:

- Local in-process execution by default.
- MCP execution when `SKILL_EROSION_MCP_URL` is set.

## Synthetic data and scenarios

The repository includes deterministic synthetic attempts and expected trend
labels:

```text
data/synthetic/attempts.csv
data/synthetic/attempts.json
data/synthetic/expected_trends.json
```

The fixtures cover:

- widening gaps
- narrowing gaps
- stable gaps
- contradictory evidence
- insufficient evidence
- multiple generated students and checkpoints

The fixture generator is:

```text
scripts/generate_synthetic.py
```

## Validation currently available

Unit tests are located in `tests/unit/test_journey.py` and cover:

- expected trend statuses
- idempotent ingestion
- conflicting-version rejection
- invalid-attempt rejection
- unknown-student handling
- scoped and versioned clustering
- ready remediation plans
- verifier confirmation and downgrade behavior
- explanation generation
- response-text redaction from serialized results

Repository checks:

```powershell
python -m compileall -q src apps scripts
python scripts/check_scaffold.py
python -m unittest discover -s tests/unit -p "test_*.py" -v
```

## Current limitations

- All data is synthetic; no real student data is supported by default.
- The scorer is deterministic and heuristic, not a trained assessment model.
- The verifier is rule-based and does not currently make an LLM call.
- Remediation uses a fixed curated catalog rather than generated resources.
- The follow-up retest currently contains one deterministic demo question.
- Parent linking is a minimal local authorization boundary, not production
  authentication; teacher and student dashboards still have no account system.
- There is no cohort-wide benchmarking.
- There are no historical multi-week visualization controls beyond the stored
  checkpoints in the current journey.
- Multiple skill domains are not presented as a single cohort workflow.
- The Streamlit dashboards use local state and are not production deployments.
- The current pipeline does not automatically schedule a day-two retest.
- Confidence calibration remains `insufficient_data` for legacy attempts that
  do not contain self-reported confidence.
- Cross-skill transfer remains `insufficient_data` unless related-skill
  metadata and two unassisted observations for each of the two skills are
  available; the dashboard currently only checks the first related skill
  listed for a given skill in the taxonomy, not all of them.
- Chroma's default embedding function downloads a ~90 MB ONNX model from
  Hugging Face on first use. This is not cached in the repository; on a
  slow or restricted network this download can fail or hang. Run the app
  once on a stable connection before relying on it offline or on
  event wifi.
