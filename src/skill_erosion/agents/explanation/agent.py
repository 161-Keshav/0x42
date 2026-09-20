from skill_erosion.logging_utils import logged_agent
from skill_erosion.contracts.models import FlagExplanation

@logged_agent
def explain_flag(trend, verification, clusters):
    if verification.trend_status != trend.status: raise ValueError("Verification does not match trend")
    if any(c.student_id!=trend.student_id or c.skill_id!=trend.skill_id for c in clusters): raise ValueError("Cluster scope does not match student and skill")
    evidence=[f"{len(trend.checkpoints)} matched checkpoints are available."]
    if trend.checkpoints:
        last=trend.checkpoints[-1]
        evidence.append(f"Latest supported result: {last.assisted_score:.0%}; independent result: {last.unassisted_score:.0%}; difference: {last.gap:.0%}.")
    if len(trend.checkpoints)>1:
        change=trend.checkpoints[-1].gap-trend.checkpoints[0].gap
        evidence.append(f"The difference changed by {change*100:+.1f} percentage points across the matched history.")
    evidence.append(f"{len(clusters)} repeated independent-work patterns met the evidence threshold.")
    return FlagExplanation(headline={"widening":"Make room for independent practice","narrowing":"The two conditions are closer","stable":"A steady learning pattern","contradictory":"Give the pattern more time","insufficient_data":"Build a little more history"}[trend.status],
        explanation=trend.explanation+" Assessment conditions can vary. Review this together with your teacher.",
        evidence_points=evidence,next_step="Ask your teacher to review the evidence and agree on a practice step; repeat a short independent check-in afterwards.")
