"""Scoped parent Q&A over one learner's existing journey result."""

from skill_erosion.contracts.models import JourneyResult
from skill_erosion.embeddings.chroma import resource_collection, query as chroma_query, upsert as chroma_upsert
from skill_erosion.data import load_resource_body, load_resource_catalog
from skill_erosion.logging_utils import get_logger, timed_agent

logger = get_logger("parent_chat")

_FORBIDDEN = (
    "score", "gap", "confidence", "misconception", "verifier", "flag",
    "other student", "peer", "cheat", "cheating",
)


@timed_agent(logger, "parent_chat")
def answer_parent_question(question: str, result: JourneyResult) -> str:
    """Answer from one student's result without exposing staff-only fields."""
    lowered = question.lower()
    has_targeted_plan = any(plan.status == "ready" for plan in result.remediation)
    has_repeated_evidence = bool(result.clusters)
    reviewer_confirmed = result.verification.verdict == "confirmed"
    if "practice" in lowered or "help" in lowered or "next" in lowered:
        plan_text = (
            "The teacher already has a targeted practice step available."
            if has_targeted_plan
            else "A short practice activity can be used until the next check-in."
        )
        answer = (
            f"The most helpful next step is a short, calm practice session for "
            f"{result.trend.skill_id} without extra tools open. {plan_text} "
            "Check in again after the next activity."
        )
    elif "progress" in lowered or "doing" in lowered or "going" in lowered:
        direction = {
            "narrowing": "independent work is catching up with supported work",
            "stable": "supported and independent work are moving together",
            "widening": "independent work needs some additional support",
        }.get(result.trend.status, "there is not enough history for a reliable update")
        answer = (
            f"The current learning pattern is that {direction}. This is a supportive "
            "learning signal, not a judgment. "
            f"{'The teacher has a clear repeated pattern to work from.' if has_repeated_evidence else 'The teacher is still gathering evidence.'} "
            f"{'The current review is consistent enough to guide the next step.' if reviewer_confirmed else 'The next check-in will help clarify the picture.'}"
        )
    else:
        answer = (
            f"The update is focused on {result.trend.skill_id}. A short, regular "
            "unassisted practice session is the best next step, followed by another "
            "check-in so progress can be reviewed over time."
        )
    catalog = [
        item for item in load_resource_catalog()
        if item["skill_id"] == result.trend.skill_id
    ]
    if catalog:
        collection = resource_collection()
        chroma_upsert(
            collection,
            ids=[item["resource_id"] for item in catalog],
            documents=[
                item["misconception"] + " " + load_resource_body(item)
                for item in catalog
            ],
            metadatas=[{"skill_id": item["skill_id"]} for item in catalog],
        )
        retrieved = chroma_query(
            collection,
            query_texts=[question],
            n_results=1,
            where={"skill_id": result.trend.skill_id},
        )
        if retrieved["ids"] and retrieved["ids"][0]:
            resource_id = retrieved["ids"][0][0]
            resource = next(
                (item for item in catalog if item["resource_id"] == resource_id),
                None,
            )
            if resource:
                guidance = load_resource_body(resource).strip().splitlines()
                guidance = next(
                    (line.strip() for line in guidance if line.strip()),
                    "",
                )
                if guidance:
                    answer += f" A teacher-curated practice idea: {guidance}"
    for forbidden in _FORBIDDEN:
        answer = answer.replace(forbidden, "learning detail")
    return answer
