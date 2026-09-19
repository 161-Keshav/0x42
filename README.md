# Agentic Slice Kit + Skill Erosion Tracker

This repository preserves the organizer's Agentic Slice Kit and integrates the
working Multi-Agent Skill Erosion Tracker implementation as a submitted
agentic slice.

## Organizer kit

The organizer kit is the reusable workflow spine:

- `slice/` - durable state, typed records, budgets, retrieval, callbacks, and
  the bounded runner
- `demo/` - the organizer demo domain and smoke flow
- `web/` - expert callback form
- `corpus/` - reference material
- `scripts/` - doctor, bakeoff, smoke, and architecture checks
- `tests/` - organizer architecture, store, budget, callback, runner, and smoke
  tests
- `docs/` - builder, designer, verifier, principles, and event guidance

Read the organizer guides first:

- [Principles brief](docs/PRINCIPLES-BRIEF.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Builder guide](docs/BUILDER.md)
- [Designer guide](docs/DESIGNER.md)
- [Verifier guide](docs/VERIFIER.md)
- [Event-day guide](docs/ON-THE-DAY.md)

The organizer kit expects Python 3.11+, an optional OpenRouter key for live
LLM integration, and can be checked with:

```powershell
python -m pytest
python scripts/doctor.py
```

## Skill Erosion Tracker

The integrated implementation tracks the difference between assisted and
unassisted student performance over time:

```text
trace collector
    -> divergence scorer
    -> verifier
    -> misconception clusterer
    -> remediation agent
    -> student explanation
    -> teacher and student UIs
```

The implementation is synthetic-data-first and includes:

- Versioned SQLite trace storage
- Idempotent ingestion and conflict detection
- Assisted/unassisted longitudinal scoring
- Noise and evidence verification
- Misconception clustering
- Curated remediation resources
- Plain-language student explanations
- Teacher decisions: intervene, monitor, or dismiss
- Cohort roll-up
- Student-initiated check-ins
- Alternative remediation requests
- Rotating follow-up questions
- Downloadable teacher summaries
- Separate runtime logs
- Optional FastMCP transport
- Parent portal with linked-learner, supportive progress updates
- Teacher queue for student-initiated check-ins
- Hint-dependency, retention, and error-pattern learning-quality signals

Key directories:

- `apps/` - Streamlit teacher and student applications
- `src/skill_erosion/` - implementation package
- `config/` - skill taxonomy
- `data/synthetic/` - deterministic demo fixtures
- `resources/remediation/` - curated intervention content
- `tests/unit/`, `tests/integration/`, `tests/evaluation/` - tracker tests
- `docs/implemented-features.md` - detailed feature inventory
- `RUN.md` - tracker setup and run instructions
- `docs/skill-erosion-architecture.md` - tracker architecture

## Run the Skill Erosion Tracker

From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts/check_scaffold.py
.\.venv\Scripts\python.exe -m unittest discover -s tests/unit -p "test_*.py" -v
```

Start the two dashboards on separate ports:

```powershell
.\.venv\Scripts\python.exe -m streamlit run apps/teacher_dashboard/app.py --server.port 8501
.\.venv\Scripts\python.exe -m streamlit run apps/student_portal/app.py --server.port 8610
.\.venv\Scripts\python.exe -m streamlit run apps/parent_portal/app.py --server.port 8503
```

Open `http://127.0.0.1:8501` for the teacher view and
`http://127.0.0.1:8610` for the student view and
`http://127.0.0.1:8503` for the parent view. Port `8610` avoids the Windows
reserved range that can include Streamlit's usual `8502` port.

The tracker uses synthetic data by default. Its SQLite database is
`data/processed/traces.sqlite3`; override it with `SKILL_EROSION_DB`.

## Validation

Run the organizer suite independently:

```powershell
python -m pytest tests
```

Run the tracker suite and checks independently:

```powershell
python -m unittest discover -s tests/unit -p "test_*.py" -v
python scripts/check_scaffold.py
python -m compileall -q src apps scripts
```

The organizer and tracker implementations are kept in separate package
directories. The integration preserves both rather than replacing one with the
other.
