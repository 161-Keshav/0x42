from skill_erosion.logging_utils import logged_agent
from datetime import datetime
from skill_erosion.contracts.models import FlagVerification

@logged_agent
def verify_flag(trend):
    reasons=[]
    n=len(trend.checkpoints)
    if n<3: reasons.append(f"Only {n} matched checkpoints; at least three are needed for a strong review signal.")
    days=0 if n<2 else (datetime.fromisoformat(trend.checkpoints[-1].timestamp)-datetime.fromisoformat(trend.checkpoints[0].timestamp)).total_seconds()/86400
    if days<14: reasons.append("History spans fewer than fourteen days; repeat the assessment before drawing conclusions.")
    if trend.status in ("contradictory","insufficient_data"): reasons.append("Evidence is incomplete or moves in conflicting directions.")
    strong=not reasons
    if strong: reasons.append(f"{n} matched checkpoints span {days:.0f} days with consistent movement.")
    reasons.append("A gap describes assessment conditions; it does not establish a cause. A teacher reviews any next action.")
    return FlagVerification(verdict="confirmed" if strong else "downgraded",
        confidence="high" if strong else "medium" if n>=2 and trend.status!="contradictory" else "low",
        trend_status=trend.status,reasons=reasons,verifier_model_version="evidence-quality-v1")
