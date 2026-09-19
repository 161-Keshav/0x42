"""End-to-end journey over five agents.

Pipeline: collect -> score -> verify -> cluster -> remediate -> explain.
Agents never call each other; they communicate through typed contracts and the
shared versioned store. Two transports:

- local (default): direct in-process calls, zero dependencies.
- mcp: genuine multi-agent RPC through a FastMCP client against a running
  server. Enable with SKILL_EROSION_MCP_URL or the mcp_url argument.

Partial evidence produces honest partial results: no clusters means no
remediation plans, and the verifier downgrades thin or noisy flags.
"""

import os
from collections.abc import Sequence
from dataclasses import asdict
from typing import Mapping

from skill_erosion.agents.divergence_scoring.agent import score_divergence
from skill_erosion.agents.explanation.agent import explain_flag
from skill_erosion.agents.misconception_clustering.agent import cluster_misconceptions
from skill_erosion.agents.remediation.agent import recommend_remediation
from skill_erosion.agents.trace_collector.agent import collect_traces
from skill_erosion.agents.verification.agent import verify_flag
from skill_erosion.logging_utils import get_logger
from skill_erosion.storage import default_repository
from skill_erosion.contracts.models import (
    Attempt,
    CheckpointScore,
    FlagExplanation,
    FlagVerification,
    JourneyResult,
    MisconceptionCluster,
    RemediationPlan,
    TrendReport,
)

logger = get_logger("pipeline")


def _attempt_payloads(attempts: Sequence[Attempt | Mapping]) -> list[dict]:
    return [asdict(a) if isinstance(a, Attempt) else dict(a) for a in attempts]


def _to_trend(data: dict) -> TrendReport:
    return TrendReport(
        **{**data, "checkpoints": [CheckpointScore(**c) for c in data["checkpoints"]]}
    )


def _run_local(
    attempts: Sequence[Attempt | Mapping] | None, student_id: str, skill_id: str
) -> JourneyResult:
    if attempts:
        collect_traces(attempts)
    logger.info("journey start: %s/%s", student_id, skill_id)
    trend = score_divergence(student_id, skill_id)
    verification = verify_flag(trend)
    clusters = cluster_misconceptions(student_id, skill_id)
    decision = default_repository().get_teacher_decision(student_id, skill_id)
    remediation = (
        []
        if decision == "dismiss"
        else [recommend_remediation(cluster, trend) for cluster in clusters]
    )
    if decision == "monitor":
        logger.info("teacher decision monitor: %s/%s", student_id, skill_id)
    explanation = explain_flag(trend, verification, clusters[0] if clusters else None)
    logger.info(
        "journey complete: %s/%s status=%s verdict=%s",
        student_id, skill_id, trend.status, verification.verdict,
    )
    return JourneyResult(
        trend=trend,
        verification=verification,
        clusters=clusters,
        remediation=remediation,
        explanation=explanation,
    )


async def _run_mcp(
    attempts: Sequence[Attempt | Mapping] | None,
    student_id: str,
    skill_id: str,
    mcp_url: str,
) -> JourneyResult:
    try:
        from fastmcp import Client
    except ImportError as exc:
        raise RuntimeError("MCP transport requires: pip install -e \".[mcp]\"") from exc

    async with Client(mcp_url) as client:
        if attempts:
            await client.call_tool("collect_traces", {"attempts": _attempt_payloads(attempts)})
        trend = _to_trend(
            (await client.call_tool(
                "score_divergence", {"student_id": student_id, "skill_id": skill_id}
            )).data
        )
        verification = FlagVerification(
            **(await client.call_tool("verify_flag", {"trend": asdict(trend)})).data
        )
        clusters = [
            MisconceptionCluster(**c)
            for c in (await client.call_tool(
                "cluster_misconceptions", {"student_id": student_id, "skill_id": skill_id}
            )).data
        ]
        remediation = [
            RemediationPlan(
                **(await client.call_tool(
                    "recommend_remediation", {"cluster": asdict(c), "trend": asdict(trend)}
                )).data
            )
            for c in clusters
        ]
        explanation = FlagExplanation(
            **(await client.call_tool(
                "explain_flag",
                {
                    "trend": asdict(trend),
                    "verification": asdict(verification),
                    "cluster": asdict(clusters[0]) if clusters else None,
                },
            )).data
        )
    return JourneyResult(
        trend=trend,
        verification=verification,
        clusters=clusters,
        remediation=remediation,
        explanation=explanation,
    )


async def run_journey(
    attempts: Sequence[Attempt | Mapping] | None,
    student_id: str,
    skill_id: str,
    mcp_url: str | None = None,
) -> JourneyResult:
    url = mcp_url or os.environ.get("SKILL_EROSION_MCP_URL")
    transport = "mcp" if url else "local"
    logger.info("journey transport=%s", transport)
    if url:
        return await _run_mcp(attempts, student_id, skill_id, url)
    return _run_local(attempts, student_id, skill_id)
