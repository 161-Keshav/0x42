# Shared UI adapters

Place an MCP client adapter, display formatting, and shared components here when
wiring the two Streamlit apps. Both views must use the same backend state and
the contracts in `src/skill_erosion/contracts/models.py`. Keep scoring and
retrieval logic out of the UI. Role enforcement belongs in the backend too.
