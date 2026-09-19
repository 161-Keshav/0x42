"""Check starter fixtures/contracts without claiming that agents are implemented."""

from collections import defaultdict
from dataclasses import fields
from datetime import datetime
from pathlib import Path
import csv
import importlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skill_erosion.contracts.models import Attempt


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    records = json.loads((ROOT / "data/synthetic/attempts.json").read_text())
    expected = json.loads((ROOT / "data/synthetic/expected_trends.json").read_text())
    taxonomy = json.loads((ROOT / "config/skill_taxonomy.json").read_text())
    skills = {item["skill_id"] for item in taxonomy["skills"]}
    keys = set()
    groups = defaultdict(dict)
    required_fields = {field.name for field in fields(Attempt)}
    for row in records:
        optional_fields = {"origin"}
        require(
            set(row) <= required_fields
            and required_fields - optional_fields <= set(row),
            "Attempt schema differs from contract",
        )
        Attempt(**row)
        key = (row["attempt_id"], row["version"])
        require(key not in keys, "Duplicate fixture version")
        keys.add(key)
        require(type(row["version"]) is int and row["version"] >= 1, "Invalid version")
        require(row["synthetic"] is True, "Only synthetic fixtures may be committed")
        require(row["skill_id"] in skills, "Unknown skill")
        require(row["task_type"] in {"code", "written", "quiz"}, "Invalid task type")
        require(row["assistance"] in {"assisted", "unassisted"}, "Invalid condition")
        require(math.isfinite(row["correctness"]) and 0 <= row["correctness"] <= 1, "Invalid correctness")
        for field in ("time_taken_seconds", "hint_count"):
            require(type(row[field]) is int and row[field] >= 0, f"Invalid {field}")
        similarity = row["similarity_to_prior"]
        require(similarity is None or (math.isfinite(similarity) and 0 <= similarity <= 1), "Invalid similarity")
        require(datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")).tzinfo is not None, "Naive timestamp")
        pair_key = (row["student_id"], row["skill_id"], row["checkpoint_id"])
        require(row["assistance"] not in groups[pair_key], "Ambiguous fixture pair")
        groups[pair_key][row["assistance"]] = row

    histories = defaultdict(list)
    for (student, skill, checkpoint), pair in groups.items():
        require(set(pair) == {"assisted", "unassisted"}, "Missing pair condition")
        assisted, unassisted = pair["assisted"], pair["unassisted"]
        for field in ("matched_task_set_id", "rubric_version", "timestamp"):
            require(assisted[field] == unassisted[field], f"Mismatched {field}")
        require(assisted["task_id"] != unassisted["task_id"], "Expected distinct matched variants")
        histories[student].append((assisted["timestamp"], assisted["correctness"] - unassisted["correctness"]))
        require(expected[student]["skill_id"] == skill, "Expected label skill mismatch")

    require(set(histories) == set(expected), "Missing expected scenario")
    for student, history in histories.items():
        history.sort()
        gaps = [gap for _, gap in history]
        if len(gaps) < 3:
            label = "insufficient_data"
        elif all(abs(b - a) < 1e-8 for a, b in zip(gaps, gaps[1:])):
            label = "stable"
        elif all(b > a for a, b in zip(gaps, gaps[1:])):
            label = "widening"
        elif all(b < a for a, b in zip(gaps, gaps[1:])):
            label = "narrowing"
        else:
            label = "contradictory"
        require(label == expected[student]["expected_status"], "Fixture trend does not match label")
        require(len(history) == expected[student]["paired_checkpoints"], "Checkpoint count mismatch")

    with (ROOT / "data/synthetic/attempts.csv").open(newline="", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    require(len(csv_rows) == len(records), "CSV row count differs")
    for json_row, csv_row in zip(records, csv_rows):
        converted = {k: "" if v is None else "true" if v is True else str(v) for k, v in json_row.items()}
        require(converted == csv_row, "CSV and JSON differ")

    catalog = ROOT / "resources/remediation/catalog.json"
    for resource in json.loads(catalog.read_text()):
        require((catalog.parent / resource["path"]).is_file(), "Missing resource")

    for module in (
        "agents.trace_collector.agent", "agents.divergence_scoring.agent",
        "agents.misconception_clustering.agent", "agents.remediation.agent",
        "orchestration.pipeline", "storage.interfaces", "embeddings.interfaces",
    ):
        importlib.import_module("skill_erosion." + module)
    print(f"PASS fixtures: {len(records)} records, {len(histories)} scenarios, CSV/JSON parity, resources, imports.")

    import asyncio
    import os
    import tempfile

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.environ["SKILL_EROSION_DB"] = str(Path(tmp) / "behavior.sqlite3")
        from skill_erosion.agents.trace_collector.agent import collect_traces
        from skill_erosion.data import load_synthetic_attempts
        from skill_erosion.orchestration.pipeline import run_journey

        attempts = load_synthetic_attempts()
        first = collect_traces(attempts)
        require(collect_traces(attempts) == first, "Reimport must be an idempotent no-op")
        conflict = Attempt(**{**records[0], "correctness": 0.01})
        try:
            collect_traces([conflict])
        except ValueError:
            pass
        else:
            raise ValueError("Conflicting version payload must be rejected")
        for student, meta in expected.items():
            result = asyncio.run(run_journey(None, student, meta["skill_id"]))
            require(result.trend.status == meta["expected_status"], f"Journey status mismatch for {student}")
            require(
                len(result.trend.checkpoints) == meta["paired_checkpoints"],
                f"Journey checkpoint mismatch for {student}",
            )
            if meta["expected_status"] == "widening":
                require(result.clusters, "Widening scenario must produce a cluster")
                require(result.remediation[0].status == "ready", "Widening plan must be ready")
                require(result.remediation[0].resource_ids == ["loops-boundaries-01"], "Wrong resource")
                require(result.verification.verdict == "confirmed", "Widening flag must be confirmed")
            if meta["expected_status"] == "insufficient_data":
                require(result.verification.verdict == "downgraded", "Thin flag must be downgraded")
            require(result.explanation.headline, f"Missing explanation for {student}")
        from skill_erosion.storage import default_repository

        default_repository().close()
        default_repository.cache_clear()
    print("PASS behavior: journeys match expected trends, idempotent ingestion, conflict rejection, remediation ready.")


if __name__ == "__main__":
    main()
