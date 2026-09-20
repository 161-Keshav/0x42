import unittest
from tests.unit.helpers import history
from skill_erosion.agents.divergence_scoring.agent import score_divergence
from skill_erosion.agents.verification.agent import verify_flag
class VerificationTests(unittest.TestCase):
    def test_strong_history_confirmed(self):
        result=verify_flag(score_divergence(history(),"s1","python.loops"))
        self.assertEqual((result.verdict,result.confidence),("confirmed","high"))
    def test_thin_noisy_and_short_history_downgraded(self):
        for attempts in (history((.1,)),history((.1,.4)),history((.1,.5,.1)),[a.model_copy(update={"timestamp":"2026-01-01T00:00:00+00:00"}) for a in history()]):
            result=verify_flag(score_divergence(attempts,"s1","python.loops"))
            self.assertEqual(result.verdict,"downgraded")
            self.assertGreater(len(result.reasons),0)
