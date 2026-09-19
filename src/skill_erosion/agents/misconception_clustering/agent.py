"""Misconception clustering over weak unassisted attempts.

Attempts are embedded with the pinned encoder and greedily grouped by cosine
similarity. Cluster summaries are matched to curated misconception descriptions
by embedding similarity, never by keyword rules.
"""

from skill_erosion.contracts.models import MisconceptionCluster
from skill_erosion.data import load_resource_catalog
from skill_erosion.embeddings.chroma import (
    attempt_collection,
    embedding_model_version,
    resource_collection,
    get as chroma_get,
    query as chroma_query,
    upsert as chroma_upsert,
)
from skill_erosion.embeddings.local import cosine
from skill_erosion.logging_utils import get_logger, timed_agent
from skill_erosion.storage import default_repository

logger = get_logger("misconception_clustering")

_WEAK_CORRECTNESS = 0.8
_MERGE_THRESHOLD = 0.30
_MIN_CLUSTER_SIZE = 2
_SUMMARY_MATCH_THRESHOLD = 0.10

def _cluster(vectors: list[list[float]]) -> list[list[int]]:
    clusters: list[list[int]] = []
    centroids: list[list[float]] = []
    for index, vector in enumerate(vectors):
        best, best_score = -1, _MERGE_THRESHOLD
        for c_index, centroid in enumerate(centroids):
            score = cosine(vector, centroid)
            if score >= best_score:
                best, best_score = c_index, score
        if best == -1:
            clusters.append([index])
            centroids.append(vector)
        else:
            clusters[best].append(index)
            members = clusters[best]
            centroids[best] = [
                sum(vectors[m][d] for m in members) / len(members) for d in range(len(vector))
            ]
    return clusters


def _summarize(texts: list[str]) -> str:
    catalog = load_resource_catalog()
    if not catalog:
        return "Recurring difficulty requiring teacher review"
    collection = _collection_for_resources(catalog)
    query = chroma_query(collection, query_texts=[" ".join(texts)], n_results=1)
    if not query["ids"] or not query["ids"][0]:
        return "Recurring difficulty requiring teacher review"
    best_id = query["ids"][0][0]
    labels = {item["resource_id"]: item for item in catalog}
    best_distance = query["distances"][0][0]
    if 1.0 - best_distance < _SUMMARY_MATCH_THRESHOLD:
        return "Recurring difficulty requiring teacher review"
    return labels[best_id]["misconception"]


def _collection_for_resources(catalog: list[dict]):
    collection = resource_collection()
    chroma_upsert(
        collection,
        ids=[item["resource_id"] for item in catalog],
        documents=[item["misconception"] for item in catalog],
        metadatas=[{"skill_id": item["skill_id"]} for item in catalog],
    )
    return collection


@timed_agent(logger, "misconception_clustering")
def cluster_misconceptions(student_id: str, skill_id: str) -> list[MisconceptionCluster]:
    """Embed weak unassisted attempts and group recurring conceptual errors."""
    history = default_repository().history(student_id, skill_id)
    weak = [a for a in history if a.assistance == "unassisted" and a.correctness < _WEAK_CORRECTNESS]
    if len(weak) < _MIN_CLUSTER_SIZE:
        return []
    collection = attempt_collection()
    ids = [f"{student_id}:{skill_id}:{a.attempt_id}:v{a.version}" for a in weak]
    chroma_upsert(
        collection,
        ids=ids,
        documents=[a.response_text for a in weak],
        metadatas=[{"student_id": student_id, "skill_id": skill_id} for _ in weak],
    )
    stored = chroma_get(
        collection,
        ids=ids,
        include=["embeddings"],
    )
    vectors = stored["embeddings"]
    groups = _cluster(vectors)
    results: list[MisconceptionCluster] = []
    for members in groups:
        if len(members) < _MIN_CLUSTER_SIZE:
            continue
        attempts = [weak[i] for i in members]
        results.append(
            MisconceptionCluster(
                cluster_id=f"{student_id}-{skill_id}-c{len(results) + 1}",
                student_id=student_id,
                skill_id=skill_id,
                concept_summary=_summarize([a.response_text for a in attempts]),
                evidence_attempt_ids=[f"{a.attempt_id}:v{a.version}" for a in attempts],
                embedding_model_version=embedding_model_version(),
            )
        )
    logger.info("clustered %s/%s -> %d cluster(s)", student_id, skill_id, len(results))
    return results
