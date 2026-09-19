"""Misconception clustering over weak unassisted attempts.

Attempts are embedded with the pinned encoder and greedily grouped by cosine
similarity. Cluster summaries are matched to curated misconception descriptions
by embedding similarity, never by keyword rules.
"""

from skill_erosion.contracts.models import MisconceptionCluster
from skill_erosion.data import load_resource_catalog
from skill_erosion.embeddings.local import HashingTextEncoder, cosine
from skill_erosion.logging_utils import get_logger
from skill_erosion.storage import default_repository

logger = get_logger("misconception_clustering")

_WEAK_CORRECTNESS = 0.8
_MERGE_THRESHOLD = 0.6
_MIN_CLUSTER_SIZE = 2
_SUMMARY_MATCH_THRESHOLD = 0.10

_encoder = HashingTextEncoder()


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
    query = _encoder.encode([" ".join(texts)])[0]
    labels = _encoder.encode([item["misconception"] for item in catalog])
    best = max(range(len(catalog)), key=lambda i: cosine(query, labels[i]))
    if cosine(query, labels[best]) < _SUMMARY_MATCH_THRESHOLD:
        return "Recurring difficulty requiring teacher review"
    return catalog[best]["misconception"]


def cluster_misconceptions(student_id: str, skill_id: str) -> list[MisconceptionCluster]:
    """Embed weak unassisted attempts and group recurring conceptual errors."""
    history = default_repository().history(student_id, skill_id)
    weak = [a for a in history if a.assistance == "unassisted" and a.correctness < _WEAK_CORRECTNESS]
    if len(weak) < _MIN_CLUSTER_SIZE:
        return []
    vectors = _encoder.encode([a.response_text for a in weak])
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
                embedding_model_version=_encoder.model_version,
            )
        )
    logger.info("clustered %s/%s -> %d cluster(s)", student_id, skill_id, len(results))
    return results
