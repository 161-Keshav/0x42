"""Descriptive signals, not causal diagnoses. Missing evidence stays missing."""
import re
from collections import Counter, defaultdict
from statistics import mean
from skill_erosion.config import skill_map

def confidence_calibration(attempts):
    rows=[a for a in attempts if a.self_reported_confidence is not None]
    if len(rows)<3: return "insufficient_data"
    bias=mean(a.self_reported_confidence-a.correctness for a in rows)
    return "overconfident" if bias>.15 else "underconfident" if bias < -.15 else "well_calibrated"

def independent_checkpoints(attempts):
    groups=defaultdict(list)
    for a in attempts:
        if a.assistance=="unassisted": groups[a.checkpoint_id].append(a)
    ordered=sorted(groups.values(),key=lambda rows:(max(a.timestamp for a in rows),rows[0].checkpoint_id))
    return [mean(a.correctness for a in rows) for rows in ordered]

def cross_skill_transfer(primary_attempts, related_skill_id=None, related_skill_attempts=None):
    if not primary_attempts or not related_skill_id or not related_skill_attempts: return "insufficient_data"
    students={a.student_id for a in primary_attempts}; skills={a.skill_id for a in primary_attempts}
    if len(students)!=1 or len(skills)!=1: return "insufficient_data"
    skill=next(iter(skills))
    if related_skill_id not in skill_map().get(skill,{}).get("related_skills",[]): return "insufficient_data"
    if any(a.student_id not in students or a.skill_id!=related_skill_id for a in related_skill_attempts): return "insufficient_data"
    primary=independent_checkpoints(primary_attempts); related=independent_checkpoints(related_skill_attempts)
    if len(primary)<2 or len(related)<2: return "insufficient_data"
    gain=primary[-1]-primary[0]; transfer_gain=related[-1]-related[0]
    if gain>.05 and transfer_gain>.05: return "positive_transfer"
    if gain>.05 and transfer_gain<=.05: return "limited_transfer"
    if gain < -.05 and transfer_gain < -.05: return "declining_in_both"
    return "stable_or_mixed"

def calculate_metrics(primary_attempts, related_skill_id=None, related_skill_attempts=None):
    attempts=list(primary_attempts)
    # Partial-credit independent responses (<1) are errors for these textual
    # pattern ratios. Normalize case/spacing/punctuation; this is not semantic clustering.
    wrong=[a for a in attempts if a.assistance=="unassisted" and a.correctness<1]
    groups=Counter(re.sub(r"[^\w]+"," ",a.response_text.lower()).strip() for a in wrong)
    followups=sorted([a for a in attempts if a.origin=="follow_up" and a.assistance=="unassisted"],key=lambda a:(a.timestamp,a.attempt_id))
    retention=None
    if len(followups)>=2 and followups[0].checkpoint_id!=followups[-1].checkpoint_id:
        first=[a.correctness for a in followups if a.checkpoint_id==followups[0].checkpoint_id]
        last=[a.correctness for a in followups if a.checkpoint_id==followups[-1].checkpoint_id]
        retention=mean(last)-mean(first)
    return {"hint_dependency_ratio":mean(a.hint_count>0 for a in attempts) if attempts else None,
      "retention_decay":retention,"error_pattern_diversity":len(groups)/len(wrong) if wrong else None,
      "repeated_error_ratio":max(groups.values())/len(wrong) if wrong else None,
      "confidence_calibration":confidence_calibration(attempts),
      "cross_skill_transfer":cross_skill_transfer(attempts,related_skill_id,related_skill_attempts)}
