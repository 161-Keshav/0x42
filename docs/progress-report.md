# Skill Erosion Tracker Progress Report

**Repository:** `161-Keshav/0x42`  
**Branch:** `integration/skill-erosion`  
**Report date:** 2026-09-19

## Completed implementation

- Integrated the end-to-end assisted-versus-unassisted learning pipeline:
  trace collection, divergence scoring, verification, misconception
  clustering, remediation, and student explanation.
- Added the parent portal with one-to-one SQLite parent-to-student linking.
- Added the parent RAG assistant, scoped to the linked learner's journey and
  teacher-curated Chroma resources.
- Added an explicit **Ask assistant** form so Enter and the submit button
  both execute the parent chat flow.
- Added student check-in requests, rotating follow-up questions, alternative
  remediation requests, teacher decisions, cohort roll-up, and downloadable
  student summaries.
- Wired confidence calibration and cross-skill transfer through the metrics
  path.
- Added teacher dashboard charts for assisted/unassisted performance, gap,
  score components, evidence volume, learning-quality ratios, cohort trend
  counts, confidence calibration, and hint dependency over time.
- Added Chroma-backed sentence embeddings for attempt and resource retrieval.
- Added privacy-safe stage logging with agent timing/result summaries,
  Chroma operation counts, stdout output, shared logs, and per-app logs.
- Extended the synthetic fixture generator with proportion-preserving
  `--extra-records N` support.

## Verification evidence

The expanded fixture set was generated with:

```text
python scripts/generate_synthetic.py --extra-records 1000
Wrote 1210 records for 131 students to ...\data\synthetic
```

Final category record counts:

```text
widening: 380
narrowing: 380
stable: 266
insufficient_data: 68
contradictory: 116
total: 1210
```

The required unit suite passed:

```text
----------------------------------------------------------------------
Ran 16 tests in 127.592s

OK
```

The scaffold check passed on the expanded fixtures:

```text
PASS fixtures: 1210 records, 131 scenarios, CSV/JSON parity, resources, imports.
```

The fresh-database end-to-end journey returned:

```text
FINAL_JOURNEY widening confirmed 1 1
FINAL_PARENT_RAG The most helpful next step is a short, calm practice session for python.loops without extra tools open. The teacher already has a targeted practice step available. Check in again after the next activity. A teacher-curated practice idea: # Loop boundaries
FINAL_ATTEMPT_COLLECTION_COUNT 611
FINAL_RESOURCE_COLLECTION_COUNT 1
```

The Streamlit AppTest click-through verified the teacher analysis and parent
chat submission:

```text
TEACHER_AFTER_RUN_ANALYSIS exception_count= 0
TEACHER_AFTER_RUN_ANALYSIS success= ['Verifier: flag CONFIRMED (medium confidence)']
PARENT_AFTER_ASK exception_count= 0
PARENT_SUCCESS ['The most helpful next step is a short, calm practice session for python.loops without extra tools open. The teacher already has a targeted practice step available. Check in again after the next activity. A teacher-curated practice idea: # Loop boundaries']
```

The embedding model is cached locally:

```text
C:\Users\ppggn\.cache\chroma\onnx_models\all-MiniLM-L6-v2\onnx\model.onnx BYTES 90387606
CACHE_TOTAL_BYTES 174510889
```

## Runtime ports

The services were run and verified on these local endpoints during the
implementation work:

| Service | Endpoint |
|---|---|
| FastMCP | `http://127.0.0.1:8000/mcp` |
| Teacher portal | `http://127.0.0.1:8501` |
| Student portal | `http://127.0.0.1:8610` |
| Parent portal | `http://127.0.0.1:8611` |

All four processes were stopped after the final verification request. The
ports were confirmed clear.

## Database recovery

The original demo database contained immutable records from an older fixture
revision. Reloading the regenerated fixtures produced:

```text
ValueError: Conflicting payload for immutable (syn-insufficient-1-cp2-unassisted, v1)
```

The old database was preserved as a timestamped `.bak` file, the stale live
database was removed, and the current 1,210-record fixture set was seeded into
a fresh database:

```text
SEEDED_ATTEMPTS 1210
SEEDED_VERSIONS 1210
DATABASE_ATTEMPTS 6
```

## Known limitations

- Data is synthetic and the scoring/verifier logic is deterministic.
- Parent authentication is a local demo authorization boundary, not
  production identity management.
- The default SQLite database must be reseeded when fixture identity or
  payloads change; immutable conflict detection is intentional.
- Streamlit currently emits a deprecation warning for
  `use_container_width`; this does not prevent the apps from running.
- The repository has no separate commit marking the earlier
  "last-known-good" working tree, so exact historical drift cannot be
  reconstructed beyond the available git commits.

