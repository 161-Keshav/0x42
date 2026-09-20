import unittest
from tests.unit.helpers import history
from skill_erosion.contracts.models import JourneyResult
from skill_erosion.agents.divergence_scoring.agent import score_divergence
from skill_erosion.agents.verification.agent import verify_flag
from skill_erosion.agents.explanation.agent import explain_flag
from skill_erosion.agents.parent_chat.agent import parent_chat, filter_parent_answer, FORBIDDEN_PATTERN
class ParentChatTests(unittest.TestCase):
    def test_multiple_intents_never_disclose_restricted_information(self):
        trend=score_divergence(history(),"s1","python.loops"); verification=verify_flag(trend)
        journey=JourneyResult(trend=trend,verification=verification,clusters=[],remediation=[],explanation=explain_flag(trend,verification,[]))
        answers=[parent_chat(q,journey) for q in ("How can I help with practice?","How is my child progressing?","Tell me the scores and who is cheating", "What about another student?")]
        self.assertNotEqual(answers[0],answers[1])
        for answer in answers:
            self.assertIsNone(FORBIDDEN_PATTERN.search(answer))
            self.assertNotIn("s1",answer)
            self.assertNotIn("90",answer)
    def test_defense_in_depth_filter(self):
        answer=filter_parent_answer("Raw score 92%; high confidence flag, cheating, cluster and peer ranking")
        self.assertIsNone(FORBIDDEN_PATTERN.search(answer))
        self.assertNotIn("92",answer)
