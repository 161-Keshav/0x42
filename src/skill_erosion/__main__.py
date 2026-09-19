"""Seeded end-to-end demo: python -m skill_erosion."""

import asyncio

from skill_erosion import __version__
from skill_erosion.agents.trace_collector.agent import collect_traces
from skill_erosion.data import load_expected_trends, load_synthetic_attempts
from skill_erosion.orchestration.pipeline import run_journey


def main() -> None:
    print(f"Skill Erosion Tracker {__version__} - synthetic demo")
    attempts = load_synthetic_attempts()
    first = collect_traces(attempts)
    second = collect_traces(attempts)
    print(f"Ingested {len(first.attempt_ids)} attempts ({first.stored_versions} versions); "
          f"reimport idempotent: {first == second}")
    expected = load_expected_trends()
    for student_id, meta in expected.items():
        result = asyncio.run(run_journey(None, student_id, meta["skill_id"]))
        trend = result.trend
        gaps = " ".join(f"{c.checkpoint_id}:{c.gap:+.2f}" for c in trend.checkpoints)
        marker = "OK" if trend.status == meta["expected_status"] else "MISMATCH"
        verification = result.verification
        print(f"[{marker}] {student_id}: {trend.status} ({gaps})")
        print(f"    verifier: {verification.verdict} ({verification.confidence}) - {verification.reasons[0]}")
        print(f"    student view: {result.explanation.headline}")
        for cluster, plan in zip(result.clusters, result.remediation):
            print(f"    cluster {cluster.cluster_id}: {cluster.concept_summary}")
            print(f"    remediation [{plan.status}]: {plan.teacher_summary}")


if __name__ == "__main__":
    main()
