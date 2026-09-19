"""Behavioral tests over a temporary SQLite store. Run: python -m unittest discover -s tests/unit."""

import asyncio
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

os.environ["SKILL_EROSION_DB"] = str(Path(tempfile.mkdtemp()) / "test.sqlite3")

from skill_erosion.agents.trace_collector.agent import collect_traces
from skill_erosion.agents.divergence_scoring.agent import score_divergence
from skill_erosion.agents.misconception_clustering.agent import cluster_misconceptions
from skill_erosion.agents.verification.agent import verify_flag
from skill_erosion.data import load_expected_trends, load_synthetic_attempts
from skill_erosion.orchestration.pipeline import run_journey
from skill_erosion.storage import default_repository


def tearDownModule():
    default_repository().close()
    default_repository.cache_clear()


class JourneyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.attempts = load_synthetic_attempts()
        cls.expected = load_expected_trends()
        cls.ingestion = collect_traces(cls.attempts)

    def test_expected_trend_statuses(self):
        for student_id, meta in self.expected.items():
            with self.subTest(student=student_id):
                report = score_divergence(student_id, meta["skill_id"])
                self.assertEqual(report.status, meta["expected_status"])
                self.assertEqual(len(report.checkpoints), meta["paired_checkpoints"])

    def test_reimport_is_idempotent_noop(self):
        again = collect_traces(self.attempts)
        self.assertEqual(again, self.ingestion)

    def test_conflicting_version_rejected(self):
        conflict = replace(self.attempts[0], correctness=0.01)
        with self.assertRaises(ValueError):
            collect_traces([conflict])

    def test_invalid_attempt_rejected(self):
        bad = replace(self.attempts[0], attempt_id="bad-attempt", correctness=1.5)
        with self.assertRaises(ValueError):
            collect_traces([bad])

    def test_unknown_student_is_insufficient_not_fabricated(self):
        report = score_divergence("nobody", "python.loops")
        self.assertEqual(report.status, "insufficient_data")
        self.assertEqual(report.checkpoints, [])

    def test_clustering_scoped_and_versioned(self):
        for student_id, meta in self.expected.items():
            clusters = cluster_misconceptions(student_id, meta["skill_id"])
            for cluster in clusters:
                self.assertEqual(cluster.student_id, student_id)
                self.assertGreaterEqual(len(cluster.evidence_attempt_ids), 2)
                self.assertTrue(all(":v" in key for key in cluster.evidence_attempt_ids))

    def test_full_journey_produces_ready_plan(self):
        result = asyncio.run(run_journey(None, "demo-widening", "python.loops"))
        self.assertEqual(result.trend.status, "widening")
        self.assertTrue(result.clusters)
        self.assertTrue(result.remediation)
        plan = result.remediation[0]
        self.assertEqual(plan.status, "ready")
        self.assertEqual(plan.resource_ids, ["loops-boundaries-01"])
        self.assertTrue(plan.teacher_summary)
        self.assertTrue(plan.student_exercise)

    def test_verifier_confirms_strong_and_downgrades_thin_flags(self):
        widening = score_divergence("demo-widening", "python.loops")
        confirmed = verify_flag(widening)
        self.assertEqual(confirmed.verdict, "confirmed")
        self.assertIn(confirmed.confidence, ("medium", "high"))
        sparse = score_divergence("demo-sparse", "python.loops")
        downgraded = verify_flag(sparse)
        self.assertEqual(downgraded.verdict, "downgraded")
        self.assertEqual(downgraded.confidence, "low")
        contradictory = score_divergence("syn-contradictory-1", "python.loops")
        self.assertEqual(verify_flag(contradictory).verdict, "downgraded")

    def test_journey_includes_verification_and_explanation(self):
        result = asyncio.run(run_journey(None, "demo-widening", "python.loops"))
        self.assertEqual(result.verification.trend_status, "widening")
        self.assertTrue(result.verification.reasons)
        self.assertTrue(result.explanation.headline)
        self.assertTrue(result.explanation.evidence_points)
        self.assertIn("demo-widening", repr(result.explanation.student_id))
        self.assertTrue(result.explanation.next_step)

    def test_results_do_not_leak_response_text(self):
        result = asyncio.run(run_journey(None, "demo-widening", "python.loops"))
        serialized = repr(result)
        self.assertNotIn("Synthetic attempt", serialized)
        self.assertNotIn("response_text", serialized)


if __name__ == "__main__":
    unittest.main()
