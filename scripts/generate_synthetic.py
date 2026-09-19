"""Regenerate synthetic fixtures: attempts.json, attempts.csv, expected_trends.json.

Deterministic. Default: 24 students, 210 records covering widening, narrowing,
stable, contradictory, and insufficient_data scenarios. Add more with --extra N.
"""

import argparse
import csv
import json
from dataclasses import fields
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skill_erosion.contracts.models import Attempt

SKILL = "python.loops"
RUBRIC = "loops-rubric-v1"
WEEK_DATES = ["2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28", "2026-10-05"]

ASSISTED_TEXT = "Synthetic explanation: range excludes the stop value."
UNASSISTED_TEXTS = [
    "Synthetic attempt: I included the stop value when tracing the loop.",
    "Synthetic attempt: I traced range as if both bounds were inclusive.",
    "Synthetic attempt: I started the loop at 1 and stopped before n.",
    "Synthetic attempt: I summed one extra element past the stop bound.",
]

DEMO_STUDENTS = {
    "demo-widening": ("widening", [0.75, 0.60, 0.45]),
    "demo-narrowing": ("narrowing", [0.45, 0.60, 0.75]),
    "demo-stable": ("stable", [0.70, 0.70, 0.70]),
    "demo-sparse": ("insufficient_data", [0.75, 0.60]),
}

CONTRADICTORY_GAPS = [0.15, 0.30, 0.13, 0.35, 0.17]


def pattern_correctness(pattern: str, index: int, weeks: int) -> list[float]:
    if pattern == "widening":
        return [round(0.78 - 0.02 * (index % 4) - 0.07 * j, 2) for j in range(weeks)]
    if pattern == "narrowing":
        return [round(0.42 + 0.02 * (index % 3) + 0.07 * j, 2) for j in range(weeks)]
    if pattern == "stable":
        return [round(0.66 + 0.03 * (index % 4), 2)] * weeks
    if pattern == "contradictory":
        gaps = CONTRADICTORY_GAPS[index % len(CONTRADICTORY_GAPS):] + CONTRADICTORY_GAPS[: index % len(CONTRADICTORY_GAPS)]
        return [round(0.85 - g, 2) for g in gaps[:weeks]]
    return [round(0.72 - 0.03 * index, 2), round(0.63 - 0.03 * index, 2)][:weeks]


def build_students(extra: int) -> dict[str, tuple[str, list[float]]]:
    students: dict[str, tuple[str, list[float]]] = dict(DEMO_STUDENTS)
    plan = [("widening", 6), ("narrowing", 6), ("stable", 4), ("contradictory", 2), ("insufficient_data", 2)]
    for pattern, count in plan:
        for i in range(count):
            weeks = 2 if pattern == "insufficient_data" else 5
            name = f"syn-{pattern.replace('_data', '')}-{i + 1}"
            students[name] = (pattern, pattern_correctness(pattern, i, weeks))
    for i in range(extra):
        pattern = "widening" if i % 2 == 0 else "narrowing"
        students[f"syn-extra-{i + 1}"] = (pattern, pattern_correctness(pattern, i + 10, 5))
    return students


def make_attempt(student: str, week: int, assistance: str, correctness: float, text: str) -> dict:
    id_prefix = student.removeprefix("demo-") if student in DEMO_STUDENTS else student
    return {
        "attempt_id": f"{id_prefix}-cp{week}-{assistance}",
        "version": 1,
        "student_id": student,
        "skill_id": SKILL,
        "task_id": f"loops-set-{week}-{assistance}",
        "matched_task_set_id": f"loops-set-{week}",
        "checkpoint_id": f"week-{week}",
        "timestamp": f"{WEEK_DATES[week - 1]}T10:00:00Z",
        "assistance": assistance,
        "task_type": "written",
        "response_text": text,
        "correctness": correctness,
        "time_taken_seconds": 180 if assistance == "assisted" else 300,
        "hint_count": 2 if assistance == "assisted" else 0,
        "rubric_version": RUBRIC,
        "synthetic": True,
        "similarity_to_prior": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extra", type=int, default=0, help="extra 5-checkpoint students")
    args = parser.parse_args()

    students = build_students(args.extra)
    records: list[dict] = []
    expected: dict[str, dict] = {}
    for student, (pattern, series) in students.items():
        for week, unassisted_correctness in enumerate(series, start=1):
            records.append(make_attempt(student, week, "assisted", 0.85, ASSISTED_TEXT))
            text = (
                UNASSISTED_TEXTS[0]
                if student in DEMO_STUDENTS
                else UNASSISTED_TEXTS[(week + len(student)) % len(UNASSISTED_TEXTS)]
            )
            records.append(make_attempt(student, week, "unassisted", unassisted_correctness, text))
        expected[student] = {
            "skill_id": SKILL,
            "expected_status": pattern,
            "paired_checkpoints": len(series),
        }

    out = ROOT / "data" / "synthetic"
    (out / "attempts.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    (out / "expected_trends.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")

    names = [f.name for f in fields(Attempt)]
    with (out / "attempts.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        for record in records:
            writer.writerow({
                k: "" if v is None else "true" if v is True else str(v)
                for k, v in record.items()
            })
    print(f"Wrote {len(records)} records for {len(students)} students to {out}")


if __name__ == "__main__":
    main()
