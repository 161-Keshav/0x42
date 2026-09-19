"""Remediation agent: cluster-scoped retrieval over the curated catalog.

The cluster summary and its evidence text are embedded and matched against
embedded resource documents. With no confident match the plan is honestly
marked `no_matching_resource`; thin evidence yields `insufficient_evidence`.
"""

from typing import Mapping

from skill_erosion.contracts.models import (
    CheckpointScore,
    MisconceptionCluster,
    RemediationPlan,
    TrendReport,
)
from skill_erosion.data import load_resource_body, load_resource_catalog
from skill_erosion.embeddings.chroma import embed_texts, resource_collection, query as chroma_query, upsert as chroma_upsert
from skill_erosion.logging_utils import get_logger, timed_agent
from skill_erosion.storage import default_repository

logger = get_logger("remediation")

_MATCH_THRESHOLD = 0.10
_MIN_EVIDENCE = 2

def _coerce_cluster(raw: MisconceptionCluster | Mapping) -> MisconceptionCluster:
    return raw if isinstance(raw, MisconceptionCluster) else MisconceptionCluster(**dict(raw))


def _coerce_trend(raw: TrendReport | Mapping) -> TrendReport:
    if isinstance(raw, TrendReport):
        return raw
    data = dict(raw)
    data["checkpoints"] = [
        c if isinstance(c, CheckpointScore) else CheckpointScore(**c)
        for c in data["checkpoints"]
    ]
    return TrendReport(**data)


def _evidence_text(cluster: MisconceptionCluster) -> str:
    repo = default_repository()
    texts: list[str] = []
    for key in cluster.evidence_attempt_ids[:3]:
        attempt_id, _, version = key.rpartition(":v")
        attempt = repo.get(attempt_id, int(version)) if version.isdigit() else None
        if attempt is not None:
            texts.append(attempt.response_text)
    return " ".join(texts)


def _best_resource(
    query_vector: list[float], skill_id: str, excluded_resource_ids: set[str]
) -> tuple[dict | None, str, float]:
    catalog = [
        resource for resource in load_resource_catalog()
        if resource["skill_id"] == skill_id
        and resource["resource_id"] not in excluded_resource_ids
    ]
    if not catalog:
        return None, "", 0.0
    collection = resource_collection()
    chroma_upsert(
        collection,
        ids=[item["resource_id"] for item in catalog],
        documents=[item["misconception"] + " " + load_resource_body(item) for item in catalog],
        metadatas=[{"skill_id": item["skill_id"]} for item in catalog],
    )
    result = chroma_query(
        collection,
        query_embeddings=[query_vector],
        n_results=1,
        where={"skill_id": skill_id},
    )
    if not result["ids"] or not result["ids"][0]:
        return None, "", 0.0
    resource_id = result["ids"][0][0]
    resource = next(item for item in catalog if item["resource_id"] == resource_id)
    score = 1.0 - result["distances"][0][0]
    return resource, load_resource_body(resource), score


def _extract_exercise(body: str) -> str:
    for paragraph in body.split("\n\n"):
        if paragraph.strip().lower().startswith("practice"):
            return " ".join(paragraph.split())
    return "Re-attempt the task without assistance and explain each step by hand."


@timed_agent(logger, "remediation")
def recommend_remediation(
    cluster: MisconceptionCluster | Mapping,
    trend: TrendReport | Mapping,
    excluded_resource_ids: list[str] | None = None,
) -> RemediationPlan:
    """Retrieve a curated resource for this cluster, carrying sources into both outputs."""
    cluster = _coerce_cluster(cluster)
    trend = _coerce_trend(trend)
    base = {
        "student_id": cluster.student_id,
        "skill_id": cluster.skill_id,
        "cluster_id": cluster.cluster_id,
    }
    if len(cluster.evidence_attempt_ids) < _MIN_EVIDENCE:
        return RemediationPlan(
            teacher_summary="Not enough evidence to characterize this misconception.",
            student_exercise="",
            resource_ids=[],
            status="insufficient_evidence",
            **base,
        )
    query = embed_texts([cluster.concept_summary + " " + _evidence_text(cluster)])[0]
    resource, body, score = _best_resource(
        query, cluster.skill_id, set(excluded_resource_ids or [])
    )
    if resource is None or score < _MATCH_THRESHOLD:
        return RemediationPlan(
            teacher_summary=f"No curated resource matches: {cluster.concept_summary}.",
            student_exercise="",
            resource_ids=[],
            status="no_matching_resource",
            **base,
        )
    gaps = [c.gap for c in trend.checkpoints]
    span = f"gap {gaps[0]:+.2f} -> {gaps[-1]:+.2f}" if gaps else "no scored checkpoints"
    teacher_summary = (
        f"{cluster.concept_summary} ({len(cluster.evidence_attempt_ids)} attempts). "
        f"Trend {trend.status}, {span}. Assign {resource['resource_id']}."
    )
    plan = RemediationPlan(
        teacher_summary=teacher_summary,
        student_exercise=_extract_exercise(body),
        resource_ids=[resource["resource_id"]],
        status="ready",
        **base,
    )
    logger.info(
        "remediating %s/%s cluster %s -> %s",
        base["student_id"], base["skill_id"], base["cluster_id"], plan.status,
    )
    return plan
