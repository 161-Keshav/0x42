import unittest
from tests.unit.helpers import history
from skill_erosion.metrics import calculate_metrics, cross_skill_transfer, confidence_calibration
class MetricsTests(unittest.TestCase):
    def test_all_confidence_categories(self):
        attempts=history()
        for bias,expected in ((0,"well_calibrated"),(.3,"overconfident"),(-.3,"underconfident")):
            rows=[a.model_copy(update={"correctness":.5,"self_reported_confidence":.5+bias}) for a in attempts]
            self.assertEqual(confidence_calibration(rows),expected)
        self.assertEqual(confidence_calibration(attempts),"insufficient_data")
    def test_transfer_is_really_wired_into_aggregator(self):
        primary=history((.6,.4,.1))
        related=history((.6,.3,.1),skill_id="python.iteration")
        self.assertEqual(cross_skill_transfer(primary,"python.iteration",related),"positive_transfer")
        metrics=calculate_metrics(primary,related_skill_id="python.iteration",related_skill_attempts=related)
        self.assertEqual(metrics["cross_skill_transfer"],"positive_transfer")
        self.assertEqual(calculate_metrics(primary)["cross_skill_transfer"],"insufficient_data")
        self.assertEqual(calculate_metrics(primary,related_skill_id="python.iteration",related_skill_attempts=history(student_id="other",skill_id="python.iteration"))["cross_skill_transfer"],"insufficient_data")
    def test_ratios_and_retention(self):
        rows=history()
        metrics=calculate_metrics(rows)
        self.assertEqual(metrics["hint_dependency_ratio"],.5)
        self.assertAlmostEqual(metrics["error_pattern_diversity"],1/3)
        self.assertEqual(metrics["repeated_error_ratio"],1)
        self.assertIsNone(metrics["retention_decay"])
        followups=[a.model_copy(update={"origin":"follow_up","assistance":"unassisted"}) for a in rows[1::2]]
        self.assertAlmostEqual(calculate_metrics(followups)["retention_decay"],-.4)
    def test_transfer_requires_distinct_checkpoints_not_question_timestamps(self):
        primary=[a.model_copy(update={"checkpoint_id":"one-checkpoint"}) for a in history((.6,.4,.1))]
        related=[a.model_copy(update={"checkpoint_id":"one-checkpoint"}) for a in history((.6,.4,.1),skill_id="python.iteration")]
        self.assertEqual(calculate_metrics(primary,"python.iteration",related)["cross_skill_transfer"],"insufficient_data")
