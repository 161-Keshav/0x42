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
from skill_erosion.agents.parent_chat.agent import answer_parent_question
from skill_erosion.agents.verification.agent import verify_flag
from skill_erosion.contracts.models import Attempt
from skill_erosion.data import load_expected_trends, load_synthetic_attempts
from skill_erosion.metrics import calculate_metrics, confidence_calibration, cross_skill_transfer
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

    def test_confidence_calibration_categories(self):
        base = self.attempts[:3]
        self.assertEqual(
            confidence_calibration([replace(a, self_reported_confidence=a.correctness) for a in base]),
            "well_calibrated",
        )
        self.assertEqual(
            confidence_calibration([replace(a, self_reported_confidence=1.0) for a in base]),
            "overconfident",
        )
        self.assertEqual(
            confidence_calibration([replace(a, self_reported_confidence=0.0) for a in base]),
            "underconfident",
        )
        self.assertEqual(confidence_calibration(base[:2]), "insufficient_data")

    def test_cross_skill_transfer(self):
        attempts = [
            replace(self.attempts[0], skill_id="python.loops", assistance="unassisted", correctness=0.4),
            replace(self.attempts[1], skill_id="python.loops", assistance="unassisted", correctness=0.8),
            replace(self.attempts[0], attempt_id="transfer-target-1", skill_id="python.iteration", assistance="unassisted", correctness=0.3),
            replace(self.attempts[1], attempt_id="transfer-target-2", skill_id="python.iteration", assistance="unassisted", correctness=0.7),
        ]
        relations = {"python.loops": ["python.iteration"]}
        self.assertEqual(
            cross_skill_transfer(attempts, "python.loops", "python.iteration", relations),
            "transfer_detected",
        )
        self.assertEqual(
            cross_skill_transfer(attempts[:2], "python.loops", "python.iteration", relations),
            "insufficient_data",
        )

    def test_calculate_metrics_wires_cross_skill_transfer(self):
        """calculate_metrics must actually call cross_skill_transfer, not
        leave it hardcoded to None regardless of evidence. This is the
        regression test for that wiring bug."""
        source_attempts = [
            replace(self.attempts[0], skill_id="python.loops", assistance="unassisted", correctness=0.4),
            replace(self.attempts[1], skill_id="python.loops", assistance="unassisted", correctness=0.8),
        ]
        related_attempts = [
            replace(self.attempts[0], attempt_id="metrics-transfer-target-1", skill_id="python.iteration", assistance="unassisted", correctness=0.3),
            replace(self.attempts[1], attempt_id="metrics-transfer-target-2", skill_id="python.iteration", assistance="unassisted", correctness=0.7),
        ]
        result = calculate_metrics(
            source_attempts,
            related_skill_id="python.iteration",
            related_skill_attempts=related_attempts,
        )
        self.assertEqual(result["cross_skill_transfer"], "transfer_detected")

        # No related-skill evidence supplied: must stay honest, not fabricate.
        result_no_evidence = calculate_metrics(source_attempts, related_skill_id="python.iteration")
        self.assertEqual(result_no_evidence["cross_skill_transfer"], "insufficient_data")

    def test_semantically_similar_misconceptions_cluster(self):
        first = replace(
            self.attempts[0],
            attempt_id="semantic-a",
            student_id="semantic-student",
            assistance="unassisted",
            correctness=0.2,
            response_text="The loop includes the final boundary value.",
        )
        second = replace(
            self.attempts[1],
            attempt_id="semantic-b",
            student_id="semantic-student",
            assistance="unassisted",
            correctness=0.2,
            response_text="I treated the stopping point as part of the range.",
        )
        collect_traces([first, second])
        clusters = cluster_misconceptions("semantic-student", "python.loops")
        self.assertTrue(clusters)
        self.assertGreaterEqual(len(clusters[0].evidence_attempt_ids), 2)

    def test_parent_chat_answers_are_safe_for_two_questions(self):
        result = asyncio.run(run_journey(None, "demo-widening", "python.loops"))
        for question in ("How is the learning going?", "What should we practice next?"):
            answer = answer_parent_question(question, result).lower()
            for forbidden in ("score", "gap", "confidence", "misconception", "verifier", "flag", "cheat"):
                self.assertNotIn(forbidden, answer)

    def test_parent_link_cannot_read_unlinked_student(self):
        repository = default_repository()
        repository.link_parent("parent-test", "demo-widening")
        self.assertEqual(repository.get_linked_student("parent-test"), "demo-widening")
        with self.assertRaises(PermissionError):
            repository.get_linked_student("parent-test", "demo-narrowing")


if __name__ == "__main__":
    unittest.main()
