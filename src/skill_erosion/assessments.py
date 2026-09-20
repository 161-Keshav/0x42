"""Small, transparent quizzes. These are practice instruments, not validated exams."""
from datetime import datetime, timezone
from statistics import mean
from uuid import uuid4
from skill_erosion.contracts.models import Attempt
from skill_erosion.agents.trace_collector.agent import collect_traces
from skill_erosion.config import load_taxonomy

QUESTIONS={
 "python.loops":[("Which values does list(range(2, 5)) contain?",["2, 3, 4","2, 3, 4, 5","3, 4, 5"],0),("How many times does range(4) iterate?",["3","4","5"],1),("What is the last value in range(1, 7, 2)?",["5","6","7"],0)],
 "python.iteration":[("What is sum([2, 3, 4])?",["4","7","9"],2),("How many elements of [1, 5, 4] are greater than 3?",["1","2","3"],1),("Starting at 1, multiply by each value in [2, 3]. What is the final total?",["5","6","3"],1)],
 "math.fractions":[("What is 1/2 + 1/3?",["2/5","5/6","1/6"],1),("Which fraction equals 1/2?",["2/4","1/4","2/3"],0),("What is 1/4 + 1/2?",["2/6","1/8","3/4"],2)],
 "math.ratios":[("For rice:water = 2:3, how much water goes with 6 cups of rice?",["7","9","12"],1),("Four notebooks cost 12 units. What do seven cost?",["15","21","28"],1),("Which ratio is equivalent to 3:5?",["6:10","6:8","4:6"],0)]}

def submit_retest(repo,student_id,skill_id,answers,confidence=.5,elapsed_seconds=0):
    questions=QUESTIONS[skill_id]
    if len(answers)!=len(questions) or any(a not in q[1] for a,q in zip(answers,questions)):
        raise ValueError("Answer every question before submitting")
    previous=repo.history(student_id,skill_id)
    if not previous: raise ValueError("Unknown student or skill")
    independent=[a for a in previous if a.assistance=="unassisted"]
    latest_cp=independent[-1].checkpoint_id if independent else None
    old_score=mean(a.correctness for a in independent if a.checkpoint_id==latest_cp) if independent else None
    checkpoint="followup-"+uuid4().hex
    now=datetime.now(timezone.utc).isoformat()
    rows=[Attempt(attempt_id=f"{checkpoint}-{i}",version=1,student_id=student_id,skill_id=skill_id,task_id=f"{skill_id}-practice-{i}",
      matched_task_set_id=f"{checkpoint}-set",checkpoint_id=checkpoint,timestamp=now,assistance="unassisted",task_type="quiz",
      response_text=answer,correctness=float(answer==q[1][q[2]]),time_taken_seconds=max(0,int(elapsed_seconds))//len(questions),hint_count=0,
      rubric_version="practice-quiz-v1",synthetic=False,origin="follow_up",self_reported_confidence=confidence)
      for i,(q,answer) in enumerate(zip(questions,answers))]
    collect_traces(rows,repo,load_taxonomy())
    return {"checkpoint_id":checkpoint,"previous_independent_score":old_score,"independent_score":mean(a.correctness for a in rows),
      "gap_change":None,"gap_message":"Gap change cannot be measured for this independent-only retest; a comparable assisted assessment is needed."}
