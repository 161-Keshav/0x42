from skill_erosion.logging_utils import logged_agent
from collections import defaultdict
from statistics import mean
from skill_erosion.contracts.models import CheckpointScore, TrendReport
MODEL_VERSION="matched-gap-v1"
NOISE=.03

@logged_agent
def score_divergence(attempts, student_id, skill_id):
    latest={}
    for a in attempts:
        if a.student_id!=student_id or a.skill_id!=skill_id: continue
        if a.attempt_id not in latest or a.version>latest[a.attempt_id].version: latest[a.attempt_id]=a
    groups=defaultdict(lambda: defaultdict(list))
    for a in latest.values(): groups[(a.checkpoint_id,a.matched_task_set_id,a.rubric_version)][a.assistance].append(a)
    paired=defaultdict(list)
    for (cp,_,_),conditions in groups.items():
        if not conditions["assisted"] or not conditions["unassisted"]: continue
        paired[cp].append(conditions)
    checkpoints=[]
    for cp,sets in paired.items():
        assisted=mean(mean(a.correctness for a in s["assisted"]) for s in sets)
        unassisted=mean(mean(a.correctness for a in s["unassisted"]) for s in sets)
        evidence=[a for s in sets for mode in ("assisted","unassisted") for a in s[mode]]
        checkpoints.append(CheckpointScore(checkpoint_id=cp,timestamp=max(a.timestamp for a in evidence),
          assisted_score=assisted,unassisted_score=unassisted,gap=assisted-unassisted,
          evidence_attempt_ids=sorted(a.evidence_id for a in evidence)))
    checkpoints.sort(key=lambda c:(c.timestamp,c.checkpoint_id))
    # <2 matched checkpoints: insufficient. All adjacent deltas <= .03: stable.
    # Widening/narrowing: >half of ALL adjacent deltas exceed +/- .03,
    # with net movement > .03 in that direction. Otherwise contradictory.
    # Each matched task set/rubric receives equal weight within its checkpoint.
    if len(checkpoints)<2: status="insufficient_data"
    else:
        deltas=[b.gap-a.gap for a,b in zip(checkpoints,checkpoints[1:])]
        net=checkpoints[-1].gap-checkpoints[0].gap
        if all(abs(d)<=NOISE for d in deltas): status="stable"
        elif sum(d>NOISE for d in deltas)>len(deltas)/2 and net>NOISE: status="widening"
        elif sum(d < -NOISE for d in deltas)>len(deltas)/2 and net < -NOISE: status="narrowing"
        else: status="contradictory"
    descriptions={"widening":"The difference between supported and independent work is increasing.",
      "narrowing":"The difference between supported and independent work is decreasing.",
      "stable":"The measured difference is steady within the noise threshold.",
      "contradictory":"The checkpoints move in conflicting directions.",
      "insufficient_data":"At least two matched checkpoints are needed to describe a trend."}
    return TrendReport(student_id=student_id,skill_id=skill_id,status=status,checkpoints=checkpoints,
        model_version=MODEL_VERSION,explanation=descriptions[status])
