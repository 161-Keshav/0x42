"""Six MCP adapters call the same agent functions used in-process."""
from functools import lru_cache
from fastmcp import FastMCP
from skill_erosion.runtime import create_pipeline
from skill_erosion.config import load_taxonomy
from skill_erosion.contracts.models import TrendReport, FlagVerification, MisconceptionCluster
from skill_erosion.agents.trace_collector.agent import collect_traces as collect
from skill_erosion.agents.divergence_scoring.agent import score_divergence as score
from skill_erosion.agents.verification.agent import verify_flag as verify
from skill_erosion.agents.misconception_clustering.agent import cluster_misconceptions as cluster_agent
from skill_erosion.agents.remediation.agent import recommend_remediation as recommend
from skill_erosion.agents.explanation.agent import explain_flag as explain
mcp=FastMCP("GapTrace local agents")
@lru_cache(maxsize=1)
def runtime():
    from skill_erosion.logging_utils import configure_logging
    configure_logging("mcp_server")
    return create_pipeline()

@mcp.tool
def collect_traces(records: list[dict]) -> dict:
    """Validate and atomically ingest versioned assessment records."""
    return collect(records,runtime().repo,load_taxonomy()).model_dump()

@mcp.tool
def score_divergence(student_id: str, skill_id: str) -> dict:
    """Score matched assisted/independent checkpoints for one student and skill."""
    rows=runtime().repo.history(student_id,skill_id)
    if not rows: raise ValueError("No assessment evidence for this student and skill")
    return score(rows,student_id,skill_id).model_dump()

@mcp.tool
def verify_flag(trend: dict) -> dict:
    """Check evidence quality with deterministic, versioned rules."""
    return verify(TrendReport.model_validate(trend)).model_dump()

@mcp.tool
def cluster_misconceptions(student_id: str, skill_id: str) -> dict:
    """Group repeated wrong independent answers using local sentence embeddings."""
    p=runtime(); p.vectors.ensure_resources()
    return {"clusters":[c.model_dump() for c in cluster_agent(p.repo.history(student_id,skill_id),p.vectors,student_id,skill_id)]}

@mcp.tool
def recommend_remediation(cluster: dict, excluded_resource_ids: list[str] | None = None) -> dict:
    """Retrieve a curated practice suggestion for teacher review."""
    p=runtime(); p.vectors.ensure_resources()
    return recommend(MisconceptionCluster.model_validate(cluster),p.vectors,excluded_resource_ids or []).model_dump()

@mcp.tool
def explain_flag(trend: dict, verification: dict, clusters: list[dict]) -> dict:
    """Explain one scoped pattern without returning response text."""
    return explain(TrendReport.model_validate(trend),FlagVerification.model_validate(verification),[MisconceptionCluster.model_validate(c) for c in clusters]).model_dump()

if __name__=="__main__": mcp.run(transport="http",host="127.0.0.1",port=8000)

