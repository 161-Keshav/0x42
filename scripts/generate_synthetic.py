"""One deterministic generator. The supplied historical baseline was unavailable."""
import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, pstdev
from skill_erosion.config import ROOT

CATEGORIES={"widening":[.10,.25,.40,.55,.70],"narrowing":[.70,.55,.40,.25,.10],"stable":[.20,.21,.20,.21,.20],"contradictory":[.10,.55,.15,.60,.10],"insufficient_data":[.20]}
WRONG={"python.loops":["I thought range(1, 5) includes the upper endpoint, so the loop visits five.","The ending boundary is counted in Python iteration; I expected range(1, 5) to reach five."],
"python.iteration":["The accumulator gets replaced by the last list item instead of adding every value.","I used the final item as the total rather than accumulating each element in the list."],
"math.fractions":["To add two fractions I add their denominators and numerators together.","I sum both bottom numbers as well as top numbers when adding fractions."],
"math.ratios":["To scale a ratio I add the same number to both quantities.","Equivalent proportions keep the difference constant by adding to each side instead of multiplying."]}

def generate(size=200):
    if size<200 or size%200: raise ValueError("Size must be a positive multiple of the 200-row baseline")
    rows=[]; expected=[]
    for replicate in range(size//200):
        for category,gaps in CATEGORIES.items():
            students=10 if category=="insufficient_data" else 2
            for local_index in range(students):
                sid=f"S-{category[0].upper()}{replicate*students+local_index+1:03d}"
                skills=("python.loops","python.iteration") if local_index%2==0 else ("math.fractions","math.ratios")
                offset=(replicate%3-1)*.005
                for skill in skills:
                    expected.append(dict(student_id=sid,skill_id=skill,status=category))
                    # Keep the first 200 records unchanged. Added scenarios deliberately
                    # span stronger effects for visual demonstration, not empirical inference.
                    scenario_gaps=list(gaps)
                    if replicate and category in ("widening","narrowing"):
                        low=.10-.005*replicate; high=.70+.025*replicate
                        scenario_gaps=[low+(high-low)*i/4 for i in range(5)]
                        if category=="narrowing": scenario_gaps.reverse()
                    elif replicate and category=="contradictory":
                        scenario_gaps=[.1,.55+.02*replicate,.15,.60+.02*replicate,.1]
                    for cp,gap in enumerate(scenario_gaps):
                        for assistance in ("assisted","unassisted"):
                            correct=.90+offset if assistance=="assisted" else .90+offset-gap
                            bias=(.25 if category=="widening" else -.20 if category=="narrowing" else 0)
                            confidence=max(0,min(1,correct+bias))
                            rows.append(dict(attempt_id=f"{sid}-{skill}-{cp}-{assistance}",version=1,student_id=sid,skill_id=skill,
                              task_id=f"{skill}-q{cp}-{assistance}",matched_task_set_id=f"{skill}-set{cp}",checkpoint_id=f"checkpoint-{cp+1}",
                              timestamp=(datetime(2026,1,5,tzinfo=timezone.utc)+timedelta(days=cp*7)).isoformat(),assistance=assistance,task_type="written",
                              response_text=WRONG[skill][cp%2] if assistance=="unassisted" and correct<.6 else "I traced each step and checked the result using the task rules.",
                              correctness=round(correct,4),time_taken_seconds=120+cp*12,hint_count=(cp+1 if assistance=="assisted" else 0),
                              rubric_version="synthetic-v1",synthetic=True,origin="system",self_reported_confidence=round(confidence,4),similarity_to_prior=None))
    return rows,expected

def summary(rows,expected):
    categories={(r["student_id"],r["skill_id"]):r["status"] for r in expected}
    counts=Counter(categories[(r["student_id"],r["skill_id"])] for r in rows)
    pairs={}
    for r in rows: pairs.setdefault((r["student_id"],r["skill_id"],r["checkpoint_id"]),{})[r["assistance"]]=r["correctness"]
    gaps=[v["assisted"]-v["unassisted"] for v in pairs.values()]
    histories={}
    for (student,skill,checkpoint),values in pairs.items():
        histories.setdefault((student,skill),[]).append((checkpoint,values["assisted"]-values["unassisted"]))
    movements={category:[] for category in CATEGORIES}
    for key,values in histories.items():
        ordered=sorted(values)
        movements[categories[key]].append(ordered[-1][1]-ordered[0][1])
    separation=mean(movements["widening"])-mean(movements["narrowing"])
    by_category={}
    for category in CATEGORIES:
        values=[v["assisted"]-v["unassisted"] for key,v in pairs.items() if categories[key[:2]]==category]
        by_category[category]={"gap_mean":round(mean(values),4),"gap_std":round(pstdev(values),4)}
    return dict(widening_narrowing_trajectory_separation=round(separation,4),mean_net_gap_change={k:round(mean(v),4) for k,v in movements.items()},per_category_gap_stats=by_category,rows=len(rows),students=len({r["student_id"] for r in rows}),category_counts=dict(counts),gap_mean=round(mean(gaps),4),gap_std=round(pstdev(gaps),4))

def write_dataset(size=200,output=None):
    out=Path(output or ROOT/"data/synthetic");out.mkdir(parents=True,exist_ok=True)
    rows,expected=generate(size)
    (out/"attempts.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
    (out/"expected_trends.json").write_text(json.dumps(expected,indent=2),encoding="utf-8")
    with (out/"attempts.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return summary(rows,expected)

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--size",type=int,default=200);args=parser.parse_args()
    baseline_rows,baseline_expected=generate(200)
    before=summary(baseline_rows,baseline_expected)
    after=write_dataset(args.size)
    comparison={"baseline_provenance":"Recreated baseline; no historical dataset was supplied.","before":before,"after":after,
      "interpretation":"The first 200 rows and all category proportions are preserved. Added widening/narrowing scenarios deliberately span stronger effects, increasing the separation of their mean net gap changes. This is synthetic scenario design, not evidence that row count improves validity."}
    (ROOT/"data/synthetic/expansion-report.json").write_text(json.dumps(comparison,indent=2),encoding="utf-8")
    print(json.dumps(comparison,indent=2))
