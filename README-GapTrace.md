# GapTrace / 0x42

A local learning notebook that compares assisted and independent assessment histories. Teacher review leads to supportive practice; a widening gap is never an accusation.

## Start on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-gaptrace.txt
.\.venv\Scripts\python.exe scripts/run_apps.py
```

Or run `./Start-GapTrace.ps1` in PowerShell. Open the teacher portal and open **Demo data** in the sidebar and select **Load / refresh synthetic data**. The parent portal becomes available after these accounts are linked by the load action.

- Teacher: http://127.0.0.1:8501
- Student: http://127.0.0.1:8502
- Parent: http://127.0.0.1:8503

Python 3.11+ is required. No API keys are needed. GapTrace never calls an external LLM. The first semantic analysis downloads Chroma's real ONNX all-MiniLM-L6-v2 model; subsequent runs use its local cache. A failed download is visible and never replaced by fake embeddings.

## Try the complete journey

1. Teacher: load the data, select `S-W001` / loop boundaries, then **Run analysis**. Inspect the paired chart, evidence review, signals and suggestions.
2. Choose **Intervene** and **Save decision** to approve the practice step. Monitor keeps the pattern visible; Dismiss suppresses suggestions.
3. Student: choose the same learner and skill, request practice, try an alternative or ask for a check-in. Submit the three-question independent retest.
4. Parent: choose `parent-S-W001`, view the learning update and ask a question. The parent agent never receives access to another learner.
5. Teacher: inspect the check-in queue and refresh the cohort overview. Download the student summary.

The local selectors demonstrate roles and account links; they are not production authentication. Use synthetic data. Before real deployment, add verified identities, access controls and a student-data retention policy.

## Commands

```powershell
.\.venv\Scripts\python.exe -m skill_erosion seed
.\.venv\Scripts\python.exe -m skill_erosion journey --student S-N001 --skill python.loops
.\.venv\Scripts\python.exe -m skill_erosion parent-chat --account parent-S-W001 --question "How can I help?"
.\.venv\Scripts\python.exe -m skill_erosion counts
.\.venv\Scripts\python.exe -m skill_erosion mcp
```

MCP listens at `http://127.0.0.1:8000/mcp`. Set `SKILL_EROSION_MCP_URL` to that URL before starting the portals to use all six remote adapters. The default runs in-process. MCP is also a trusted local demo endpoint; no public binding or authentication is supplied.

Set environment variables as shown in `.env.example`: `cp .env.example .env`, paste your OpenRouter key, and the `SKILL_EROSION_*` block below it (data directory, logging level, shared log path, optional MCP URL) is read from the same file now - one `.env` for both the organizer's kit and GapTrace itself.

## Verify

```powershell
.\.venv\Scripts\python.exe -m compileall -q src apps scripts
.\.venv\Scripts\python.exe scripts/check_scaffold.py
.\.venv\Scripts\python.exe -m unittest discover -s tests/unit -p "test_*.py" -v
```

See `docs/implemented-features.md` for the final evidence report and `docs/verification/` for actual command output. Tests use real Chroma embeddings and isolated temporary databases. The original organizer tests require `pip install -r requirements.txt`; live-provider tests remain separate from GapTrace and need their own API key.

## Interpretation

Scoring and verification are deterministic rules. Semantic matching is local MiniLM similarity; thresholds and practice questions are pilot choices, not validated diagnostics. Related-skill transfer describes co-movement, not a causal effect. Unpaired follow-up retests can show independent change but cannot establish a new assisted–independent gap.

The supplied workspace contained only the build spec. The original fork and historical baseline were unavailable. The retrieved public starter kit is preserved byte-for-byte with a revision and SHA-256 manifest. The new generator recreates a documented 200-attempt baseline and expands it to 1,200 with unchanged category proportions and a deliberately broader range of synthetic trend strengths. These are transparent synthetic scenarios, not research findings.


## Interface and local services

The three portals share an offline Manrope font, a light forest-green theme, responsive layouts, and keyboard focus styles. The teacher's first screen previews the real matched assessment history. Run analysis still performs evidence verification and finds practice resources. Student exercises still require teacher approval, and parent questions remain scoped to the linked learner.

The launcher starts one Chroma service at `127.0.0.1:8504` for the three portals. Chroma's embedded client is [not safe for multiple writer processes](https://cookbook.chromadb.dev/core/system_constraints/). The portal processes, CLI, and MCP adapters find the shared service through a data-directory-specific descriptor and verify its instance token. An unavailable or mismatched service fails visibly instead of opening another writer. Restart `scripts/run_apps.py` to recover a stale descriptor. With no launcher descriptor, isolated scripts and tests still use embedded Chroma.

Manrope is bundled under its [SIL Open Font License](src/skill_erosion/assets/OFL.txt). No remote font request is needed. See [the UI refinement verification](docs/verification/ui-refinement.md) for browser and regression checks.
