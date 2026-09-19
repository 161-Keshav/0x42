# Implementation roadmap

The skeleton is complete when the package imports, sample data is consistent,
four tool boundaries exist, and architecture/docs are available. This does not
complete the proposal's working-demo milestone.

## Phase 1 - Foundation

- [ ] Review and freeze `config/skill_taxonomy.json` and `contracts/models.py`.
- [ ] Implement JSON/CSV normalization and strict trace validation.
- [ ] Implement SQLite append-only versions and idempotent import in `storage/`.
- [ ] Select/pin an open-source encoder and implement `TextEncoder`.
- [ ] Implement persistent Chroma indexing with version/model metadata and retry.
- [ ] Add ingestion/restart/reimport tests before integrating real agent calls.

Acceptance: one synthetic submission and its revision survive restart; an exact
reimport creates no duplicate; invalid input is rejected; raw text never appears
in captured logs. Scoring may remain explicitly unavailable at this stage.

## Phase 2 - Core intelligence

- [ ] Build matching and structured feature extraction under `scoring/`.
- [ ] Train/calibrate a lightweight ensemble and record model/feature versions.
- [ ] Implement divergence trends with insufficient and contradictory states.
- [ ] Cluster weak attempts semantically with retained evidence references.
- [ ] Index curated resources and retrieve using each cluster's misconception.
- [x] Implement `run_journey` using six independently callable FastMCP tools.
- [ ] Add unit tests and held-out evaluation journeys for all result states.

Acceptance: one full seeded journey produces a longitudinal trend, an evidence
cluster, a targeted exercise, and a teacher summary. Missing history/resources
must yield honest partial results. Each agent must be testable independently.

## Phase 3 - Interfaces and hardening

- [ ] Connect both apps through the shared server-side client adapter.
- [ ] Plot both performance series and the gap in the teacher view.
- [ ] Display one targeted exercise with a source in the student view.
- [ ] Add follow-up attempt submission and integrate the next checkpoint.
- [ ] Verify sparse, contradictory, empty-cluster, and retrieval-failure cases.
- [ ] Rehearse a clearly labeled synthetic demonstration and document limitations.

Acceptance: a teammate can clone, start the system, and reproduce a complete
student journey. Real-data deployment requires authorization, redaction, access
control, and retention implementation beyond this scaffold.
