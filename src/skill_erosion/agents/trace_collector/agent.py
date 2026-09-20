from skill_erosion.logging_utils import logged_agent
from skill_erosion.contracts.models import Attempt
from skill_erosion.storage.interfaces import AttemptRepository

@logged_agent
def collect_traces(records, repo: AttemptRepository, taxonomy):
    known={s["skill_id"] for s in taxonomy["skills"]}
    attempts=[r if isinstance(r,Attempt) else Attempt.model_validate(r) for r in records]
    for a in attempts:
        if a.skill_id not in known: raise ValueError(f"Unknown skill: {a.skill_id}")
    return repo.store(attempts)
