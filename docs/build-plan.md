# GapTrace implementation plan
Spec: 13-one-shot-build-spec.md, supplied and approved by the user.
Architecture: independent typed agents, versioned SQLite, persistent local Chroma ONNX embeddings, three Streamlit processes, six FastMCP tools. No external LLM calls.
Execute sequentially, testing each agent before proceeding:
1. Contracts, taxonomy, SQLite and collector: validation, atomic conflicts, idempotency, account scoping.
2. Divergence scorer: matched task sets and rubrics, versioned evidence, five trend categories.
3. Verifier: checkpoint count, history duration and contradictory movements.
4. Clusterer: real semantic embeddings, repeated wrong independent evidence only.
5. Remediation: semantic catalog retrieval and exclusions.
6. Explanation and parent chat: isolated student data, explicit forbidden-term filtering.
7. Metrics and orchestration: related-skill aggregator regression, persistence, decision gates, MCP parity.
8. Three UIs: exercise every control using Streamlit AppTest; charts, cohort, download and retests.
9. Logging: stdout and shared/app files, scoped summaries and vector counts.
10. Synthetic generator: establish absent 200-row baseline, expand same generator to 1200 proportionally.
11. Full verification: compile, scaffold hashes, unittest, original offline tests, three health checks, MCP HTTP.
12. Evidence report organized by spec sections with actual command output.

Explicit choices: the fork and historical dataset were absent. Preserve retrieved upstream bytes and record its revision. Create a clearly identified reproducible baseline. No claims of historical fork identity or empirical population validity. Only teacher-approved intervene releases exercises; monitor/pending remains informational and dismiss suppresses plans. Unpaired follow-ups report independent change but never invent a paired gap. Parent account selection is a local demo, not production identity authentication.
