import unittest
from tests.unit.helpers import history, record
from skill_erosion.contracts.models import Attempt
from skill_erosion.agents.divergence_scoring.agent import score_divergence

class ScoringTests(unittest.TestCase):
    def test_five_scenarios(self):
        for gaps,status in [((.1,.3,.5),"widening"),((.5,.3,.1),"narrowing"),((.2,.21,.2),"stable"),((.1,.5,.1),"contradictory"),((.2,),"insufficient_data")]:
            with self.subTest(status=status):
                trend=score_divergence(history(gaps),"s1","python.loops")
                self.assertEqual(trend.status,status)
                self.assertAlmostEqual(trend.checkpoints[-1].gap,gaps[-1])
                self.assertTrue(all("@v" in e for c in trend.checkpoints for e in c.evidence_attempt_ids))
    def test_unmatched_and_rubric_mismatch_are_not_pairs(self):
        attempts=history()
        attempts[1]=Attempt(**record(1,matched_task_set_id="other"))
        attempts[3]=Attempt(**record(3,rubric_version="v2"))
        self.assertEqual(score_divergence(attempts,"s1","python.loops").status,"insufficient_data")
    def test_student_scope_and_latest_version(self):
        attempts=history()+history(student_id="other")
        attempts.append(Attempt(**record(1,version=2,correctness=.8)))
        report=score_divergence(attempts,"s1","python.loops")
        self.assertEqual(len(report.checkpoints),3)
        self.assertIn("a1@v2",report.checkpoints[0].evidence_attempt_ids)
        self.assertNotIn("a1@v1",report.checkpoints[0].evidence_attempt_ids)
    def test_equal_task_set_weight(self):
        attempts=history((.2,))
        attempts += [Attempt(**record(10+i,checkpoint_id="cp-0",matched_task_set_id="set-2",correctness=v)) for i,v in enumerate((.6,.2))]
        report=score_divergence(attempts,"s1","python.loops")
        self.assertAlmostEqual(report.checkpoints[0].gap,.3)
