# Team collaboration guide

## Suggested work ownership

Assign people to these workstreams; one person may own more than one.

| Workstream | Owned folders | First deliverable |
|---|---|---|
| Data and ingestion | `agents/trace_collector/`, `storage/`, `config/`, `data/` | One versioned record survives restart |
| Scoring and evaluation | `agents/divergence_scoring/`, `scoring/`, `models/`, `tests/evaluation/` | Matched trends plus sparse-history output |
| Semantic intelligence | `agents/misconception_clustering/`, `agents/remediation/`, `embeddings/`, `retrieval/`, `resources/` | Cluster evidence plus a specific exercise |
| UI and integration | `apps/`, `orchestration/`, `mcp_server.py`, `tests/integration/` | Both views consume one student journey |

Agent and backend paths are under `src/skill_erosion/`. Coordinate changes to
`contracts/models.py`, `pyproject.toml`, and the taxonomy across all owners.

## Manual GitHub handoff

1. Create your GitHub repository and use this folder's contents as the root.
2. Include hidden `.github`, `.gitignore`, and `.env.example` files. If uploading
   with the browser, check that hidden files were not skipped.
3. Exclude virtual environments, caches, local databases, raw submissions, and
   model artifacts. The prepared ZIP includes only handoff files.
4. Add your teammates as collaborators and assign workstreams in issues.
5. Have each teammate follow the README setup commands after cloning.

This scaffold has not initialized Git, created a remote, or pushed anything.
Choose a license with the team before presenting the project as open source;
no license has been assumed on your behalf.

## Working together

Use branches such as `feat/trace-ingestion`, `feat/divergence-scoring`, or
`feat/teacher-view`. Keep each pull request focused on one behavior. Use the PR
template to state contract changes and test evidence. Prefer a teammate review
before merging into `main`.

Before opening a pull request, run the scaffold checks and the behavioral tests
for your component. Never change fixture expected labels just to match a failing
algorithm. New dependencies should be declared in `pyproject.toml`; avoid committing
one developer's full environment freeze. Freeze a reproducible dependency set once
the initial integrated stack is working.
