# GapTrace implementation and verification report

Verification date: 19 September 2026. This report describes the code and artifacts actually exercised, rather than planned work. All commands use the project `.venv` Python. Start with [README-GapTrace.md](../README-GapTrace.md).

## 0. Organizer starter kit

**VERIFIED WORKING** — All 54 retrieved organizer files are byte-identical to public upstream revision `090662b5de1601cb19debab3cc077d7028f41d28`. New code lives alongside them. Original requirements and README are preserved; the addition uses `requirements-gaptrace.txt` and `README-GapTrace.md`.

```text
slice/: 9 original files present and byte-identical
demo/: 9 original files present and byte-identical
web/: 2 original files present and byte-identical
docs/: 9 original files present and byte-identical
scripts/: 4 original files present and byte-identical
tests/: 7 original files present and byte-identical
docs/PRINCIPLES-BRIEF.md: present
docs/ARCHITECTURE.md: present
docs/DESIGNER.md: present
docs/BUILDER.md: present
docs/VERIFIER.md: present
docs/ON-THE-DAY.md: present
docs/SPEC-TEMPLATE.md: present
Upstream revision: 090662b5de1601cb19debab3cc077d7028f41d28
Protected files: 54; new required files: 13; failures: 0
```

[Full hash manifest](verification/upstream-manifest.json) · [Repository checks](verification/repository-checks.txt). Provenance: [public organizer repository](https://github.com/rsimhan/agentic-slice-kit/tree/090662b5de1601cb19debab3cc077d7028f41d28).

**COULD NOT VERIFY** — Identity with the team's historical fork point: the supplied folder contained only the build specification, with no Git checkout or fork history. The retrieved public revision is the documented preservation baseline.

## 0b. Working method and evidence

**VERIFIED WORKING** — Foundation, scorer, verifier, embeddings, remediation, explanation and parent agent were exercised separately before orchestration and the UIs. The full final suite passes. Actual transcripts are retained in [verification](verification/). Review-discovered faults were reproduced before repair; see section 14.

## 1–3. Purpose and constraints

**VERIFIED WORKING** — Assisted/independent histories describe learning conditions. Teacher decisions persist, monitor retains evidence, dismiss suppresses plans, and only intervene releases a student practice step. No automated accusation, parent notification, proctoring, recording, or test-access block is in the new application. Parent communication is initiated by the parent. The real journey test checks the human decision gate.

**COULD NOT VERIFY** — The background research assertions in the supplied spec were not treated as established findings. The shipped UI and project guide make no claim of clinical validation, proven causation, or exhaustive uniqueness against every existing product.

## 4–6. Layout, technology and contracts

**VERIFIED WORKING** — Python package, three Streamlit entry points, SQLite schema, taxonomy, resources, local Chroma and six MCP adapters compile and pass scaffold checks. Pydantic validates required fields, bounds, finite values, timestamps, assistance and origins. All agent outputs use the typed contracts. Invalid records and unknown skills are rejected. CSV and JSON produce the same stored records.

[Data contract](data-contract.md) · [Tested package versions](verification/environment.json).

```text
python -m compileall -q src apps scripts
(no output)
Exit code: 0
python -m pip check
No broken requirements found.
Exit code: 0
```

## 7. Agents

| Agent | Status and executable proof |
| --- | --- |
| 7.1 Trace collector | **VERIFIED WORKING** — `test_ingestion_is_idempotent`, `test_versions_append_and_conflicts_are_atomic`, `test_invalid_records_rejected`, CSV/JSON expansion test. Repeat import stores zero new versions; conflicting batches roll back. |
| 7.2 Divergence scorer | **VERIFIED WORKING** — `test_five_scenarios`, rubric/task-set mismatch, latest version and equal-task-set-weight tests. All 216 expanded student/skill histories match their expected statuses. Rules and noise threshold are explicit in source. |
| 7.3 Verifier | **VERIFIED WORKING** — Tests confirm long, repeated evidence and downgrade thin, short or contradictory histories. |
| 7.4 Misconception clusterer | **VERIFIED WORKING** — Real ONNX embeddings group two differently-worded loop errors; unrelated geography and plant answers remain outside that cluster. Scope, current versions, unassisted/wrong filtering and minimum repetition are tested. |
| 7.5 Remediation | **VERIFIED WORKING** — Real catalog embeddings return an exercise, an excluded-ID alternative, no match for an unrelated query, and insufficient evidence for a thin cluster. |
| 7.6 Explanation | **VERIFIED WORKING** — Evidence includes checkpoint counts and measured gaps. Serialized explanations exclude raw answers and cluster labels; foreign-student clusters are refused. |
| 7.7 Parent chat | **VERIFIED WORKING** — Multiple intents generate distinct supportive templates. An explicit forbidden-term filter is applied to every answer. No raw questions, responses, scores, confidence, cluster labels or other-student data are copied into answers. |

Proof: [final unit test output](verification/unit-tests.txt), [live teacher and parent transcript](verification/teacher-terminal-and-log.txt), [MCP HTTP proof](verification/mcp-http.txt).

## 8. Persistent Chroma

**VERIFIED WORKING** — Real default all-MiniLM-L6-v2 ONNX embeddings; no hash, keyword or fake-vector fallback. After a teacher loop journey and a parent iteration journey, collection counts are:

```text
CHROMA COUNTS {"skill-erosion-attempts": 20, "skill-erosion-resources": 8}
```

This is exactly ten current attempts for each of two analyzed skills, plus eight curated resources. The remaining cohort records live in SQLite and are embedded when analyzed. The HTTP MCP run independently produced ten attempt embeddings and eight resources on its isolated server. [Actual proof](verification/teacher-terminal-and-log.txt).

## 9. SQLite and parent scope

**VERIFIED WORKING** — Append-only consecutive attempt revisions, latest scoped history, exact-version evidence lookup, atomic conflicts, persisted analyses, teacher decisions and one-to-one parent links. `history_for_parent` and `Pipeline.for_parent` reject a requested student outside the linked account, including direct function calls.

**VERIFIED WORKING** — Ungraded check-in requests persist as `CheckInTrace` events with `origin=student_initiated`, separately from graded attempts. This conservative extension avoids inventing correctness for a request for help. They appear in the teacher's separate queue. [Journey, foundation and portal tests](verification/unit-tests.txt).

## 10. Learning-quality metrics

**VERIFIED WORKING** — Hint ratio, independent textual error diversity, repeated-error ratio, confidence calibration and related-skill transfer are computed. Retention compares first/last independent follow-up checkpoint means; it remains missing until there are two distinct follow-up checkpoints. Error-pattern ratios normalize text; the separate misconception agent uses semantic embeddings.

The public aggregator receives both primary and related-skill attempts. A regression prevents separate question timestamps within one checkpoint from masquerading as longitudinal evidence.

```text
CALCULATE_METRICS RELATED SKILLS {"hint_dependency_ratio": 0.5, "retention_decay": null, "error_pattern_diversity": 0.6, "repeated_error_ratio": 0.4, "confidence_calibration": "underconfident", "cross_skill_transfer": "positive_transfer"}
```

[Actual journey/aggregator output](verification/teacher-terminal-and-log.txt) · `test_transfer_is_really_wired_into_aggregator` · `test_transfer_requires_distinct_checkpoints_not_question_timestamps`.

## 11. Logging

**VERIFIED WORKING** — Every agent logs its name, student/skill scope, result summary and elapsed time. Chroma logs collection and operation counts. Python logging writes to stdout, shared `skill_erosion.log` and the appropriate app file. Level and shared-path overrides are implemented. No raw answer or full attempt payload is passed to loggers.

The following is copied from the actual teacher app log during a Streamlit AppTest journey; the enclosing transcript separately contains its stdout output:

```text
2026-09-19 22:55:49,590 INFO agent=collect_traces event=start student_id=multiple(108) skill_id=multiple(4)
2026-09-19 22:55:49,624 INFO agent=collect_traces event=complete student_id=multiple(108) skill_id=multiple(4) stored_versions=1200 elapsed_ms=33.63
2026-09-19 22:55:51,096 INFO chroma operation=upsert collection=skill-erosion-resources items=8
2026-09-19 22:55:51,726 INFO agent=score_divergence event=start student_id=S-W001 skill_id=python.loops
2026-09-19 22:55:51,726 INFO agent=score_divergence event=complete student_id=S-W001 skill_id=python.loops status=widening elapsed_ms=0.61
2026-09-19 22:55:51,727 INFO agent=verify_flag event=start student_id=S-W001 skill_id=python.loops
2026-09-19 22:55:51,727 INFO agent=verify_flag event=complete student_id=S-W001 skill_id=python.loops verdict=confirmed confidence=high elapsed_ms=0.13
2026-09-19 22:55:51,727 INFO agent=cluster_misconceptions event=start student_id=S-W001 skill_id=python.loops
2026-09-19 22:55:51,727 INFO chroma operation=upsert collection=skill-erosion-attempts items=10
2026-09-19 22:55:52,319 INFO chroma operation=query collection=skill-erosion-attempts items=1 stored_items=10
2026-09-19 22:55:52,503 INFO chroma operation=query collection=skill-erosion-attempts items=1 stored_items=10
2026-09-19 22:55:52,675 INFO chroma operation=query collection=skill-erosion-attempts items=1 stored_items=10
2026-09-19 22:55:52,848 INFO chroma operation=query collection=skill-erosion-resources items=1 stored_items=8
2026-09-19 22:55:53,024 INFO agent=cluster_misconceptions event=complete student_id=S-W001 skill_id=python.loops count=1 elapsed_ms=1297.12
2026-09-19 22:55:53,027 INFO agent=recommend_remediation event=start student_id=S-W001 skill_id=python.loops
2026-09-19 22:55:53,027 INFO chroma operation=query collection=skill-erosion-resources items=1 stored_items=8
2026-09-19 22:55:53,213 INFO agent=recommend_remediation event=complete student_id=S-W001 skill_id=python.loops status=ready elapsed_ms=185.98
2026-09-19 22:55:53,213 INFO agent=explain_flag event=start student_id=S-W001 skill_id=python.loops
2026-09-19 22:55:53,213 INFO agent=explain_flag event=complete student_id=S-W001 skill_id=python.loops result=ready elapsed_ms=0.12
```

[Terminal output and actual file content](verification/teacher-terminal-and-log.txt). `test_stdout_shared_and_app_log_have_redacted_agent_summary` checks both files and stdout.

## 12. Synthetic expansion

**VERIFIED WORKING** — One generator produces JSON, CSV and expected trends. Its first 200 records are unchanged in the final 1,200-row output. The category proportions are exactly maintained, confidence values are populated, and each student has two related skills.

| Measure | Recreated baseline | Expanded |
| --- | ---: | ---: |
| Attempts | 200 | 1,200 |
| Students | 18 | 108 |
| Each of the five categories | 40 | 240 |
| Mean paired gap | 0.3008 | 0.3148 |
| Paired-gap standard deviation | 0.1899 | 0.2135 |
| Widening–narrowing mean net trajectory separation | 1.2 | 1.35 |

Added scenarios deliberately span stronger effects, so their trajectories are easier to distinguish. This is a property of the synthetic scenario design, not a claim that increasing sample count improves measurement validity. [Full before/after output](verification/synthetic-expansion.txt).

**COULD NOT VERIFY** — The historical 200-row dataset and its category proportions were not supplied. The equal-category baseline is explicitly recreated, not claimed to be the missing original.

The earlier development store was preserved at `data/processed-before-scenario-expansion`; final fixtures were loaded into a fresh `data/processed` store to avoid changing existing attempt versions silently.

## 13. Three UIs and control wiring

**VERIFIED WORKING** — Three independent processes launched, all returned live HTTP health responses, and all project controls below were exercised against actual functions/storage. Streamlit AppTest covers the full control journey; the browser additionally rendered teacher charts, a student request and the parent answer.

```text
http://127.0.0.1:8501/_stcore/health HTTP 200 ok
http://127.0.0.1:8502/_stcore/health HTTP 200 ok
http://127.0.0.1:8503/_stcore/health HTTP 200 ok
```

| Portal/control | Actual action and verification |
| --- | --- |
| Teacher — Load / refresh synthetic data | Validated ingestion + parent-link seeding; AppTest reload and idempotent tests. |
| Teacher — Student selector | Scoped repository lookup; AppTest selects S-W001. |
| Teacher — Skill selector | Scoped skill history; AppTest selects python.loops. |
| Teacher — Run analysis | Full persisted journey; AppTest and live browser. |
| Teacher — Intervene / Monitor / Dismiss | Each radio choice saved and read back in the portal test; dismissal removes plans. |
| Teacher — Save decision | SQLite update followed by a new journey; AppTest. |
| Teacher — Checkpoint evidence expander | Displays the journey's versioned checkpoint table; old evidence survives revised attempts. |
| Teacher — Refresh cohort overview | Computes all student/skill trend/verdict/confidence/calibration rows and both count charts; AppTest asserts populated cohort. |
| Teacher — Download student summary | Generated text registered by Streamlit; live HTTP attachment body matched the persisted summary exactly. |
| Student — Load / refresh synthetic data | Same validated ingestion; AppTest exercises the button. |
| Student — Student / Skill selectors | Scoped lookup and session reset; AppTest. |
| Student — Request personalized practice | Full journey with numeric explanation; teacher-approved plan only; AppTest and live browser. |
| Student — Request a check-in | Stores an ungraded trace; AppTest asserts queue entry. |
| Student — This exercise did not help | Semantic retrieval excluding used IDs for the displayed plan's cluster; local and MCP regression tests. |
| Student — Three varied question inputs | Three actual questions for each of four skills; submission validates all answers. |
| Student — Confidence slider | Included in the three saved follow-up attempts; AppTest changes its value. |
| Student — Submit independent retest | Deterministic grading, new checkpoint, persisted attempts and re-run journey; AppTest verifies result and follow-up rows. |
| Parent — Parent account selector | `get_linked_student` is the sole resolution path; switching accounts resets prior answers; AppTest. |
| Parent — View learning update | Scoped journey + supportive parent template + independent/follow-up counts; AppTest. |
| Parent — Ask a question / Ask | Exactly one question field; real parent agent returns its answer immediately below the same form; AppTest and live browser. |

Charts: assisted/independent, gap and hint ratio over checkpoints; cohort trend counts by skill and calibration-category counts. Learning signals display computed values or explicit insufficient data. Tabs organize review/cohort/queue and practice/retest.

```text
DOWNLOAD HTTP 200; content-type=text/plain; charset=utf-8; content-disposition=attachment; filename="gaptrace-S-W001.txt"; bytes=882; payload matches persisted student summary.
Parent question inputs: 1; source line 37 at the original verification
```

[Current parent source trace](verification/parent-input-trace.txt) · [Portal interactions](verification/portal-tests.txt) · [Download payload](verification/download.txt).

**VERIFIED WORKING** — Independent retests report the measured independent-score change. They explicitly state that gap change cannot be established without a comparable assisted retest. No assisted result is invented. Retest score comparisons are labelled descriptive because question difficulty may differ.

## 14. Full verification and repaired regressions

**VERIFIED WORKING** — Required unittest discovery and the repository's default pytest workflow both pass:

```text
$ python -m unittest discover -s tests/unit -p "test_*.py" -v
----------------------------------------------------------------------
Ran 32 tests in 46.454s

OK

$ python -m pytest -q
103 passed, 3 skipped, 10 subtests passed in 49.10s
```

[Full unittest transcript](verification/unit-tests.txt) · [Full pytest transcript](verification/full-pytest.txt) · [Original organizer suite](verification/organizer-tests.txt).

**COULD NOT VERIFY** — Three original organizer live-provider tests are skipped because no provider key is configured. They are separate from GapTrace; its local tests are not skipped.

**VERIFIED WORKING** — Four review-discovered regressions were repaired and are now covered:

| Reproduced failure | Specific fix | Passing regression |
| --- | --- | --- |
| One checkpoint returned `positive_transfer` | Aggregate by checkpoint ID, then order checkpoint means by timestamp. | Metrics distinct-checkpoint test. |
| Fresh MCP client returned `no_matching_resource` for an alternative | Route alternative lookup through the configured MCP server. | MCP real-store parity test and HTTP alternative proof. |
| Ready plan from a later cluster queried cluster zero | Resolve the first displayed ready plan to its aligned cluster. | Journey alternative-cluster test. |
| Revised attempts raised `KeyError` for cached `@v1` evidence | Resolve chart evidence against all stored versions. | Portal test appends version 2 then rerenders the existing analysis. |

[Recorded MCP failure before repair](verification/mcp-regression-before.txt) · [Cluster failure](verification/cluster-regression-before.txt) · [Chart failure](verification/portal-regression-before.txt). Chroma and log handles are also explicitly closed during test cleanup on Windows. A Unicode display issue found in the live browser was corrected.

## 15. MCP support

**VERIFIED WORKING** — Exactly six tools, in-process parity, and actual HTTP orchestration selected through `SKILL_EROSION_MCP_URL`:

```text
HTTP TOOLS ["cluster_misconceptions", "collect_traces", "explain_flag", "recommend_remediation", "score_divergence", "verify_flag"]
HTTP JOURNEY widening confirmed remediation ready
HTTP ALTERNATIVE ready ['loops-trace-table']
SKILL_EROSION_MCP_URL execution: VERIFIED
HTTP SERVER COLLECTIONS {"skill-erosion-attempts": 10, "skill-erosion-resources": 8}
```

Run `python -m skill_erosion mcp` to serve loopback port 8000. Run `python scripts/verify_mcp_http.py` for an isolated, reproducible HTTP check.

## 16–17. Deliverables and current limitations

**VERIFIED WORKING** — Source, tests, curated resource files, 1,200-row fixtures, CLI, local launcher, data contract, this report and command transcripts are present. Re-run `python scripts/verify_ui_evidence.py` to reproduce the teacher/parent log and embedding-count proof with isolated storage.

**COULD NOT VERIFY** — Real-world learning outcomes and assessment validity. This is a synthetic local pilot; scoring, verification, explanations and parent chat are deterministic rules/templates, while semantic grouping/retrieval uses local MiniLM embeddings.

**COULD NOT VERIFY** — Production authentication and multi-tenant isolation are outside this pilot. The account selector demonstrates linked-account scoping; it is not authenticated identity. Apps and MCP bind to loopback only. Real deployments need identity and role authorization before accepting real student records.

**COULD NOT VERIFY** — First-use ONNX model download availability on another machine. It succeeded here and cached the actual model. On a restricted network, Chroma-dependent features raise a visible logged error; there is no silent fallback.

**VERIFIED WORKING** — No API key is required for GapTrace. No external LLM is called. The organizer's original optional LLM-based kit remains untouched and separate.


## UI refinement, 20 September 2026

The teacher, student and parent portals have been visually refined with a bundled local font, shared theme, responsive layouts and native interactive charts. The data, model rules, review gates and parent scoping remain intact. A pre-existing multi-process Chroma index error discovered during browser QA was fixed by introducing one loopback search service with instance-token validation. See `docs/verification/ui-refinement.md` and the corresponding regression outputs for the current proof.
