# One-Shot Build Specification: Skill Erosion Tracker (GapTrace / 0x42)

This is a complete, standalone specification. Do not ask clarifying
questions before starting — every decision needed to build this is
answered somewhere in this document. Where something is genuinely
ambiguous, make the most conservative, most honest choice (favor
"insufficient_data" over a guessed number, favor a smaller working slice
over a larger broken one) and state the choice you made in your final
report.

This document exists because a previous agent working on this project
repeatedly reported features as "implemented" when they were not actually
wired into the running pipeline, or silently changed working code without
flagging it. The verification requirements in this document are not
optional extras — they are the actual deliverable, as important as the
code itself. A feature with no proof it runs is treated as not built.

---

## 0. This repo is a fork of the organizer's starter kit — keep their files intact

**The team was told the base repository is `github.com/rsimhan/agentic-slice-kit`,
forked for this event, and the requirement is to keep the organizer's given
files and folders intact — not to delete, rename, or break anything under
`slice/`, `demo/`, `web/`, `docs/`, `scripts/`, or the top-level test files
that shipped with the kit.** Beyond that, the team is free to add whatever
additional files, folders, or approach best fits the project — there is no
requirement to route the skill-erosion system through the kit's `slice/`
state machine, its `llm.py` call point, or its `retrieve.py` vector search.
Those are available to use if useful, not mandatory.

This project's actual implementation — `src/skill_erosion/`, `apps/`,
Chroma for vector search, the FastMCP tools, the three Streamlit apps — is
exactly that kind of addition: new files alongside the organizer's kit,
not a replacement of it. **The only thing to verify is that nothing under
the organizer's original folders was deleted or altered**, not that the
skill-erosion build integrates with them.

### Verification requirement for this section

- Confirm `slice/`, `demo/`, `web/`, and the organizer's `docs/` files
  (`PRINCIPLES-BRIEF.md`, `ARCHITECTURE.md`, `DESIGNER.md`, `BUILDER.md`,
  `VERIFIER.md`, `ON-THE-DAY.md`, `SPEC-TEMPLATE.md`) are still present
  and unmodified from the fork. A simple file listing plus, if git history
  is available, `git diff` against the original fork point, is enough
  proof — this doesn't need a deep integration check.

---

## 0b. Non-negotiable working method

- **Never report something as done without pasting the actual command
  output that proves it.** "Implemented X" is not acceptable; "implemented
  X, here is the test output / log output / function call result proving
  it" is the only acceptable form of a status report.
- **Never silently change or remove something that was working.** If a
  change to one part requires touching another, say so explicitly before
  and after.
- **Never hardcode a value to make a signal "available" when the real
  computation isn't wired up.** If evidence is genuinely insufficient,
  return `"insufficient_data"` (or equivalent), never a fabricated number
  or a silently-always-None placeholder.
- **Work in this order and do not skip ahead:** foundation and contracts
  first, then each agent one at a time with its own test before moving to
  the next, then orchestration, then the three UIs, then logging, then
  synthetic data expansion, then a full end-to-end verification pass. If
  time runs out, a smaller number of fully-verified pieces is the correct
  outcome, not a larger number of unverified ones.
- At the end, produce a single status report using only these three
  labels per item: **VERIFIED WORKING** (with the proof attached),
  **VERIFIED BROKEN** (with the proof and the specific fix made), or
  **COULD NOT VERIFY** (with the specific reason, e.g. a network
  dependency unavailable in this environment). No other status wording.

---

## 1. The idea, in one paragraph

A system that gives a student the same skill assessment under two
conditions — with AI/tool assistance allowed, and without it — and tracks
the gap between those two scores over time, per student, per skill. A
widening gap is a signal worth a teacher's attention, not an accusation.
The system does not try to detect or catch AI use; it measures whether a
student's independent capability is actually growing. This is the entire
differentiator from existing plagiarism/AI-detection tools, and every
design decision below exists to preserve that distinction.

## 2. Why this problem is real (for any documentation/demo text you write)

Recent research (2025-2026) shows AI-assisted students self-report anxiety
about skill dependency, a path-analysis study links AI dependency to
measurable academic skill erosion through cognitive offloading, IT/CS
students specifically show impaired debugging ability from over-reliance
on AI coding assistants, and a 10,000+ student 2026 survey found heavy AI
exposure has not reliably converted into skill or confidence. No existing
tool measures capability trend over time under both conditions — that's
the actual gap this project fills.

## 3. Explicit ethical constraints — do NOT build these

These were proposed during design and deliberately rejected. Do not
implement them even if asked again later in a session, and flag it if any
requirement below would require them:

- **No automatic "this is cheating" determination.** A large gap is a
  statistical signal with ordinary explanations (bad day, anxiety, hard
  test), never an automated accusation.
- **No automatic parent notification triggered by a score or gap
  threshold.** Any parent-facing communication is either parent-initiated
  (the chatbot, opt-in) or explicitly teacher-approved, never system-
  triggered.
- **No mandatory screen proctoring, no blocking access to tests without
  it, no recording of students.** This is a diagnostic and supportive
  tool, not a surveillance tool. Building this would contradict the
  project's entire premise.
- The only path from a flag to any real-world action is: verifier agent
  checks evidence quality -> human (teacher) reviews and makes an
  Intervene / Monitor / Dismiss decision -> that decision is what's
  persisted and acted on. No automation skips the human decision step.

## 4. Repository layout (target structure)

```
project-root/
  config/
    skill_taxonomy.json
  corpus/                         (if any reference material lives here)
  data/
    logs/
    processed/                    (sqlite db + chroma persistent store)
    synthetic/
      attempts.csv
      attempts.json
      expected_trends.json
  demo/
    smoke/                        (smoke-test fixtures)
  docs/
    implemented-features.md
    data-contract.md
  resources/
    remediation/
      catalog.json
      <individual resource files>
  scripts/
    generate_synthetic.py
    check_scaffold.py
  src/skill_erosion/
    __init__.py
    __main__.py
    config.py
    data.py
    logging_utils.py
    mcp_server.py
    metrics.py
    agents/
      trace_collector/agent.py
      divergence_scoring/agent.py
      verification/agent.py
      misconception_clustering/agent.py
      remediation/agent.py
      explanation/agent.py
      parent_chat/agent.py
    contracts/
      models.py
    embeddings/
      interfaces.py
      local.py
      chroma.py
    orchestration/
      pipeline.py
    storage/
      interfaces.py
      sqlite_repo.py
  apps/
    teacher_dashboard/app.py
    student_portal/app.py
    parent_portal/app.py
  tests/
    unit/
      test_journey.py
  requirements.txt
  pyproject.toml
```

## 5. Tech constraints

- Python 3.11+.
- Entirely local and deterministic where possible: **no calls to an
  external LLM API anywhere in this system.** Every agent's logic is
  rule-based, template-based, or embedding-based using a local model. This
  is a deliberate choice, not a limitation to fix — it keeps the system
  auditable, free to run, and honest about what it can and can't detect.
  If a future version adds a real LLM call, that is a separate explicit
  decision, not assumed here.
- Storage: SQLite for all structured/relational data (attempts, decisions,
  parent links). Chroma (persistent client, local, no server) for vector
  search, using its default local embedding function
  (`all-MiniLM-L6-v2` via ONNX, downloaded and cached on first use).
- UI: three independent Streamlit apps, one per audience (teacher,
  student, parent), each its own process, each its own port
  (8501/8502/8503 by convention).
- Six FastMCP tools exposing the same agent functions for independent/
  programmatic invocation, separate from the UIs.
- Dependencies (minimum): `pydantic`, `streamlit`, `pandas`, `fastmcp`,
  `chromadb`, `pytest`/`unittest` (stdlib is fine for tests).
- **Build all of this as new files/folders alongside the organizer's kit**
  (`src/skill_erosion/`, `apps/`, `tests/unit/`, `docs/implemented-features.md`,
  etc., as laid out in section 4) — do not modify, delete, or route through
  `slice/`, `demo/`, or `web/`. Those stay exactly as the fork provided
  them.

## 6. Core data contract

Defined as typed dataclasses (or pydantic models) in
`contracts/models.py`. Agents communicate only through these typed
objects, never by calling each other's internals directly.

```python
Assistance = Literal["assisted", "unassisted"]
TrendStatus = Literal["widening", "stable", "narrowing", "insufficient_data", "contradictory"]

Attempt:
  attempt_id: str
  version: int
  student_id: str
  skill_id: str
  task_id: str
  matched_task_set_id: str
  checkpoint_id: str
  timestamp: str (ISO 8601)
  assistance: Assistance
  task_type: Literal["code", "written", "quiz"]
  response_text: str
  correctness: float (0.0-1.0)
  time_taken_seconds: int
  hint_count: int
  rubric_version: str
  synthetic: bool
  similarity_to_prior: float | None = None
  origin: Literal["system", "student_initiated", "follow_up"] = "system"
  self_reported_confidence: float | None = None   # optional, 0.0-1.0

IngestionResult: attempt_ids: list[str], stored_versions: int

CheckpointScore:
  checkpoint_id, timestamp, assisted_score, unassisted_score, gap,
  evidence_attempt_ids: list[str]

TrendReport:
  student_id, skill_id, status: TrendStatus, checkpoints: list[CheckpointScore],
  model_version: str, explanation: str

FlagVerification:
  verdict: Literal["confirmed", "downgraded"], confidence: Literal["low","medium","high"],
  trend_status: TrendStatus, reasons: list[str], verifier_model_version: str

MisconceptionCluster:
  student_id, skill_id, concept_summary: str, evidence_attempt_ids: list[str],
  embedding_model_version: str

RemediationPlan:
  status: Literal["ready","no_matching_resource","insufficient_evidence"],
  teacher_summary: str | None, student_exercise: str | None,
  resource_ids: list[str]

FlagExplanation:
  headline: str, explanation: str, evidence_points: list[str], next_step: str

JourneyResult:
  trend: TrendReport, verification: FlagVerification,
  clusters: list[MisconceptionCluster], remediation: list[RemediationPlan],
  explanation: FlagExplanation
```

`config/skill_taxonomy.json` shape:
```json
{
  "version": "pilot-v1",
  "skills": [
    {"skill_id": "python.loops", "name": "Loop boundaries and iteration",
     "domain": "introductory_python", "related_skills": ["python.iteration"]},
    {"skill_id": "python.iteration", "name": "Iteration reasoning transfer check",
     "domain": "introductory_python", "related_skills": ["python.loops"]}
  ]
}
```
Add more skills/domains as needed for the expanded dataset (section 12),
keeping every skill's `related_skills` populated where a genuine
relationship exists, since cross-skill transfer depends on this.

## 7. Agents — exact required behavior

Each agent lives in its own module under `agents/<name>/agent.py`, is
independently unit-testable, and is exposed as its own FastMCP tool.

### 7.1 Trace collector (`collect_traces`)
- Validates incoming attempt records (required fields present, correctness
  in [0,1], skill_id known to the taxonomy).
- Rejects invalid records and conflicting versions explicitly (don't
  silently drop or silently overwrite).
- Stores in the versioned SQLite repository, scoped by student and skill.
- Repeated ingestion of the same records is a no-op (idempotent), proven
  by a test that ingests twice and asserts no duplicate rows and no
  version bump.
- Supports CSV and JSON fixture ingestion for synthetic data.

### 7.2 Divergence scorer (`score_divergence`)
- Matches assisted and unassisted attempts by checkpoint and task set.
- Computes assisted score, unassisted score, and gap per checkpoint.
- Classifies overall trend: `widening`, `stable`, `narrowing`,
  `insufficient_data`, `contradictory`. Define these precisely (e.g.
  widening = gap increasing across the majority of consecutive
  checkpoints beyond a small noise threshold; contradictory = no
  consistent direction; insufficient_data = fewer than 2 matched
  checkpoints) and write this definition into the code as a comment, not
  just implied by the implementation.
- Must never fabricate a trend when there isn't enough matched history —
  `insufficient_data` is the correct output, not a guess.
- Returns evidence attempt IDs per checkpoint and a versioned scorer name
  string (so a later change to the scoring logic is traceable in stored
  results).

### 7.3 Verifier (`verify_flag`)
- Takes a trend report and checks evidence quality: thin evidence (too
  few checkpoints), short history, contradictory movement.
- Confirms strong flags, downgrades noisy/insufficient ones.
- Returns verdict, confidence (low/medium/high), trend status, a list of
  human-readable reasons, and a verifier model/version string.
- Rule-based, not an LLM call (see section 5).

### 7.4 Misconception clusterer (`cluster_misconceptions`)
- Groups a student's repeated *wrong, unassisted* attempts for a skill by
  semantic similarity, using real sentence embeddings (Chroma + local
  embedding function — see section 8), not keyword matching.
- Produces student- and skill-scoped clusters with a plain-language
  concept summary and versioned evidence attempt IDs.
- Does not fabricate a cluster from insufficient repeated evidence
  (require a minimum count, e.g. at least 2-3 similar wrong attempts,
  before forming a cluster).
- **Verification requirement:** write a test proving that two
  semantically similar but differently-worded wrong answers cluster
  together, and that two unrelated wrong answers do not. This is the test
  that proves embeddings are actually being used, not just present in the
  codebase.

### 7.5 Remediation agent (`recommend_remediation`)
- Matches a misconception cluster to a curated resource catalog via
  embedding similarity (Chroma), not exact tag matching.
- Produces separate teacher and student outputs (teacher summary,
  student-facing exercise text, resource IDs).
- Status is one of `ready`, `no_matching_resource`, `insufficient_evidence`
  — again, never fabricate a plan when there's no real match.
- Supports "give me a different resource, excluding resource ID X" for
  the student portal's "this didn't help" control (section 9.2).

### 7.6 Explanation agent (`explain_flag`)
- Explains one student's own flag in plain language: headline, explanation,
  evidence points, next step.
- Uses only that student's own trend/verification/cluster data — must not
  expose raw response text or any other student's data. Write a test that
  serializes the result and asserts raw response text and other students'
  identifiers do not appear anywhere in the output.

### 7.7 Parent chat agent (`parent_chat` — not necessarily an MCP tool,
called directly from the parent portal)
- Takes a free-text question plus one student's own `JourneyResult`
  (already scoped — this agent must never be given access to look up a
  different student).
- Answers with template/rule-based logic keyed on question intent
  (practice/help, progress/status, fallback), optionally enriched by a
  Chroma similarity check against the curated resource catalog to note
  when a relevant resource exists.
- **Must never surface:** raw scores, verifier confidence, misconception
  cluster labels, peer/other-student comparisons, or any accusatory
  language ("cheat", "cheating", "flag" in the sense of an accusation).
  Implement this as an explicit forbidden-term filter applied to every
  generated answer, in addition to writing the templates carefully in the
  first place (defense in depth, not either/or).
- **Verification requirement:** test at least two different question
  phrasings against the same student's result and assert none of the
  forbidden terms appear in either answer.

## 8. Chroma / vector store — exact requirements

- Persistent local client at `data/processed/chroma`.
- Two collections: `skill-erosion-attempts` (attempt/misconception
  embeddings) and `skill-erosion-resources` (remediation catalog
  embeddings).
- Use Chroma's default embedding function (`all-MiniLM-L6-v2`, ONNX,
  downloaded once and cached under `~/.cache/chroma/onnx_models/` on
  first use — this requires network access the first time only).
- **Verification requirement:** after running one full journey and one
  parent-chat call, print the actual item count in each collection
  (`collection.count()`). A connected client with zero stored items is
  not proof of a working RAG pipeline — the count must be non-zero and
  must match expectations from what was ingested.
- **Known risk to document, not silently work around:** if the ONNX model
  download fails (slow/restricted network), Chroma-dependent features
  will error. Do not implement a silent fallback to a fake/no-op
  embedding — if this happens, it must be a visible error in the logs,
  not a quietly degraded feature.

## 9. Storage — SQLite requirements

- Versioned attempt repository: append-only with version tracking,
  student/skill-scoped history queries, idempotent re-import, explicit
  conflict rejection for incompatible versions (don't silently pick one).
- Teacher decisions table: `(student_id, skill_id, decision)` where
  decision is `intervene` / `monitor` / `dismiss`, persisted and read back
  on the next analysis run. A `dismiss` decision suppresses remediation
  for that student/skill until changed; `monitor` keeps the flag visible
  without altering the underlying trend computation.
- Parent links table: `(parent_account_id, student_id)`, one-to-one for
  this version. `get_linked_student(parent_account_id)` must be the only
  way the parent portal resolves which student to show — **no student
  selection dropdown anywhere in the parent portal.**
- **Verification requirement:** a test proving a parent account cannot
  retrieve another student's data, even by direct function call (not just
  "the UI doesn't offer it" — the backend must refuse it).

## 10. Metrics (`metrics.py`)

All of the following, computed honestly (return `insufficient_data`/`None`
rather than a fabricated value when evidence is thin):

- `hint_dependency_ratio` — fraction of attempts using at least one hint.
- `retention_decay` — correctness change between first and last follow-up
  attempt (requires at least 2 follow-ups; `None` otherwise).
- `error_pattern_diversity` — distinct wrong-answer patterns divided by
  total wrong answers, among unassisted attempts.
- `repeated_error_ratio` — largest repeated-error group size divided by
  total wrong answers.
- `confidence_calibration` — compares `self_reported_confidence` to actual
  correctness; returns `well_calibrated` / `overconfident` /
  `underconfident` / `insufficient_data` (require at least 3 attempts with
  confidence values; use a bias threshold, e.g. ±0.15, to classify).
- `cross_skill_transfer` — **this is the one that broke last time; get
  the function signature right the first time.** It needs evidence from
  *two* skills (the scored skill and a related skill from the taxonomy),
  not just the single skill's history. Design `calculate_metrics` to
  accept the primary skill's attempts plus an optional
  `related_skill_id` and `related_skill_attempts` parameter, and only
  compute a real transfer status when a second skill's attempts are
  actually supplied — otherwise return `insufficient_data`, don't hardcode
  it to `None` regardless of what's passed in. **Write an end-to-end test
  that calls `calculate_metrics` itself** (not just the inner
  `cross_skill_transfer` function in isolation) and asserts a real,
  non-`None`, non-placeholder result when both skills' evidence is
  supplied. This exact bug (function correct in isolation, never actually
  called by the aggregator) is what went wrong before — the test must
  catch that specific failure mode, not just test the math.

## 11. Logging

- Use Python's `logging` module. Extend, don't replace, if a
  `logging_utils.py` already exists in your working copy.
- Every agent call logs: which agent ran, key scoping inputs (student_id,
  skill_id — **never raw response_text or full attempt content**), a
  summary of what it returned (status/verdict/count — not the full
  payload), and elapsed time.
- Every Chroma operation (upsert, query) logs the collection name and item
  count involved, so a silent zero-item operation is visible in the log
  instead of hidden.
- Log to both a per-app file under `data/logs/` (e.g.
  `teacher_dashboard.log`, `student_portal.log`, `parent_portal.log`, plus
  a shared `skill_erosion.log`) and to stdout/terminal simultaneously.
- Level controlled by `SKILL_EROSION_LOG_LEVEL` env var, default `INFO`.
- Log path override via `SKILL_EROSION_LOG`.
- **Verification requirement:** run one full journey through the teacher
  dashboard and paste both the actual terminal output and the actual log
  file content, showing each agent firing in order with its inputs/outputs
  summary.

## 12. Synthetic data — expand to ~1200 entries

- Current baseline is ~200 entries across these categories: widening
  gaps, narrowing gaps, stable gaps, contradictory evidence, insufficient
  evidence, spread across multiple synthetic students and checkpoints.
- Extend the existing generator (`scripts/generate_synthetic.py`), don't
  write a second one, to add ~1000 more entries **at the same proportional
  category distribution as the current ~200** — print the actual before
  and after per-category counts so this is checkable, not asserted.
- Populate `self_reported_confidence` on generated attempts (already
  partially done — keep it) and ensure enough students/skills have
  `related_skills` populated with sufficient paired evidence for
  `cross_skill_transfer` to actually produce non-`insufficient_data`
  results on at least some students, so the metric is demonstrable, not
  just theoretically correct.
- **Verification requirement:** after expansion, show before/after summary
  statistics (e.g. mean/spread of the assisted-unassisted gap) proving the
  larger dataset makes trends more visually distinguishable in the
  dashboard charts, not just larger in row count.
- Re-run the full test suite against the expanded dataset and confirm
  nothing regresses.

## 13. UI requirements

### 13.1 Teacher dashboard (`apps/teacher_dashboard/app.py`, port 8501)
- Load/refresh synthetic data button.
- Student selector, "Run analysis" button.
- Verifier status/confidence/reasons, suggested next update.
- Mentor decision controls: Intervene / Monitor / Dismiss, persisted and
  applied on next analysis.
- Trend status, latest gap, scorer version.
- **Charts:** assisted-vs-unassisted line chart, gap-over-time line chart,
  hint-dependency-ratio-over-time line chart (derived from per-checkpoint
  evidence attempts).
- Checkpoint evidence table.
- Misconception clusters, remediation plan status and teacher summary.
- Learning-quality signals panel: hint dependency, retention decay,
  error-pattern diversity, confidence calibration, cross-skill transfer —
  all showing real computed values or an honest "insufficient data"
  message, never a hardcoded placeholder.
- Student-initiated check-in queue, shown separately from system-generated
  flags (filter on `origin == "student_initiated"`).
- Cohort roll-up: table of all students' trend/verdict/confidence/
  calibration, **plus** a bar chart of trend-status counts per skill and a
  bar chart of confidence-calibration category counts across the cohort.
- Downloadable plain-text (or docx) student summary.

### 13.2 Student portal (`apps/student_portal/app.py`, port 8502)
- Student selector, load/refresh data.
- "Request a personalized practice step" — triggers the journey, shows
  why (evidence points, in concrete numbers, not just a headline), next
  step, targeted exercise and source resource when available.
- "Something feels off — request a check-in" button — creates a
  student-initiated trace.
- "This exercise did not help" — requests an alternative remediation
  resource from the same cluster, excluding the one just shown, and
  reports honestly if no alternative exists.
- Follow-up retest: at least 2-3 varied questions per skill (not one
  fixed question), submitted as a new checkpoint, journey re-run, UI
  reports whether the independent score moved and whether the gap
  narrowed.

### 13.3 Parent portal (`apps/parent_portal/app.py`, port 8503)
- Parent account selector, resolved to exactly one linked student
  server-side — **no student dropdown.**
- "View learning update" — supportive, trend-oriented status in plain
  language (see section 7.7 for tone constraints).
- Evidence shown as independent/follow-up check-in counts, never raw
  scores or verifier confidence.
- **Exactly one** "ask a question" input, wired to the real parent chat
  agent, with the answer appearing directly below that same input, not
  buried in an unrelated expander and not duplicated as a second, unwired
  input elsewhere on the page. If you add explanatory text above the
  input, keep it as static copy only — do not create a second interactive
  element that looks like a chat box but isn't wired to anything. This
  exact bug (a second, disconnected-looking input above the real one)
  happened in a previous version of this app — check for it explicitly
  before calling this done.

## 14. Testing

- `tests/unit/test_journey.py` (or split into multiple files if that's
  cleaner, but keep them discoverable via
  `python -m unittest discover -s tests/unit -p "test_*.py"`).
- Cover, at minimum: expected trend statuses per synthetic scenario,
  idempotent ingestion, conflicting-version rejection, invalid-attempt
  rejection, unknown-student handling, scoped/versioned clustering,
  semantically-similar-misconceptions-cluster-together, ready remediation
  plans, verifier confirm/downgrade behavior, explanation generation,
  response-text redaction, confidence calibration categories (all four),
  cross-skill transfer both at the function level and the
  `calculate_metrics` aggregator level (the specific regression this
  document calls out in section 10), parent chat forbidden-term
  filtering, parent-link scoping refusal.
- Repository-level checks to run and paste output from:
  ```
  python -m compileall -q src apps scripts
  python scripts/check_scaffold.py
  python -m unittest discover -s tests/unit -p "test_*.py" -v
  ```

## 15. MCP support

Expose these six tools via FastMCP (`src/skill_erosion/mcp_server.py`):
`collect_traces`, `score_divergence`, `verify_flag`,
`cluster_misconceptions`, `recommend_remediation`, `explain_flag`.
Orchestrator runs agents in-process by default; supports MCP execution
when `SKILL_EROSION_MCP_URL` is set.

## 16. Documentation to produce

- `docs/implemented-features.md` — describe only what's actually verified
  working per section 0's rules, organized to mirror this spec's section
  numbering so a reader can cross-check claim against proof.
- A "Current limitations" section that's honest about what's still
  synthetic-only, what's rule-based rather than ML-based, and the Chroma
  network-download risk (section 8).

## 17. Definition of done

All of the following must be true, each with pasted proof, before this is
considered complete:

- [ ] Full test suite passes (or every failure is explained as an
      environment limitation, not a code defect, with evidence).
- [ ] `cross_skill_transfer` produces a real, non-placeholder result when
      evidence exists, proven via a `calculate_metrics`-level test.
- [ ] Chroma collections show non-zero item counts after a real journey
      run, with the actual counts pasted.
- [ ] All three Streamlit apps launch without error and every button/
      input on every page is confirmed wired to a real function call, not
      just present in the markup — listed explicitly, one line per
      control.
- [ ] The parent portal has exactly one working question input, verified
      by tracing the actual current file content, not assumed from an
      earlier version.
- [ ] Synthetic dataset expanded to ~1200 entries at the original
      proportional category distribution, with before/after counts shown.
- [ ] Logging fires at every agent stage, visible in both terminal and
      file output, pasted from a real run.
- [ ] None of the rejected features in section 3 were built.
- [ ] `docs/implemented-features.md` matches what was actually verified,
      not what was attempted.

If time runs out before every box is checked, stop and report exactly
which are done, which are broken, and which weren't reached — do not
extend "in progress" work into a false "done" claim to complete the list.
