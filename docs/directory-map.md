# Directory map

This is the handoff structure. Generated Python caches are omitted.

```text
skill-erosion-tracker/
|-- .github/
|   |-- ISSUE_TEMPLATE/
|   |   `-- feature.md
|   |-- workflows/
|   |   `-- checks.yml
|   `-- pull_request_template.md
|-- apps/
|   |-- shared/
|   |   `-- README.md
|   |-- student_portal/
|   |   `-- app.py
|   `-- teacher_dashboard/
|       `-- app.py
|-- config/
|   `-- skill_taxonomy.json
|-- data/
|   |-- processed/
|   |   `-- README.md
|   |-- raw/
|   |   `-- README.md
|   |-- synthetic/
|   |   |-- attempts.csv
|   |   |-- attempts.json
|   |   |-- expected_trends.json
|   |   `-- README.md
|   `-- vector_store/
|       `-- README.md
|-- docs/
|   |-- diagrams/
|   |   |-- architecture.mmd
|   |   |-- architecture.png
|   |   `-- architecture.svg
|   |-- proposal/
|   |   `-- proposal.pdf
|   |-- skill-erosion-architecture.md
|   |-- data-contract.md
|   |-- directory-map.md
|   |-- roadmap.md
|   `-- team-guide.md
|-- models/
|   `-- artifacts/
|       `-- README.md
|-- resources/
|   `-- remediation/
|       |-- catalog.json
|       `-- loop-boundaries.md
|-- scripts/
|   |-- check_scaffold.py
|   `-- render_architecture.py
|-- src/
|   `-- skill_erosion/
|       |-- agents/
|       |   |-- divergence_scoring/
|       |   |   |-- __init__.py
|       |   |   `-- agent.py
|       |   |-- misconception_clustering/
|       |   |   |-- __init__.py
|       |   |   `-- agent.py
|       |   |-- remediation/
|       |   |   |-- __init__.py
|       |   |   `-- agent.py
|       |   |-- trace_collector/
|       |   |   |-- __init__.py
|       |   |   `-- agent.py
|       |   `-- __init__.py
|       |-- contracts/
|       |   |-- __init__.py
|       |   `-- models.py
|       |-- embeddings/
|       |   |-- __init__.py
|       |   `-- interfaces.py
|       |-- orchestration/
|       |   |-- __init__.py
|       |   `-- pipeline.py
|       |-- privacy/
|       |   `-- README.md
|       |-- retrieval/
|       |   `-- README.md
|       |-- scoring/
|       |   `-- README.md
|       |-- storage/
|       |   |-- __init__.py
|       |   `-- interfaces.py
|       |-- __init__.py
|       |-- __main__.py
|       `-- mcp_server.py
|-- tests/
|   |-- evaluation/
|   |   `-- README.md
|   |-- integration/
|   |   `-- README.md
|   `-- unit/
|       `-- README.md
|-- .env.example
|-- .gitignore
|-- pyproject.toml
`-- README.md
```

Read `docs/team-guide.md` for ownership and `docs/roadmap.md` for implementation tasks.
