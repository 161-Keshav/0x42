import unittest
from tests.unit.helpers import history
from skill_erosion.contracts.models import MisconceptionCluster
from skill_erosion.agents.divergence_scoring.agent import score_divergence
from skill_erosion.agents.verification.agent import verify_flag
from skill_erosion.agents.explanation.agent import explain_flag
class ExplanationTests(unittest.TestCase):
    def test_explanation_redacts_responses_and_cluster_labels(self):
        attempts=history()
        trend=score_divergence(attempts,"s1","python.loops")
        c=MisconceptionCluster(student_id="s1",skill_id="python.loops",concept_summary="SECRET RAW RESPONSE",evidence_attempt_ids=["a1@v1","a3@v1"],embedding_model_version="test")
        result=explain_flag(trend,verify_flag(trend),[c])
        serialized=result.model_dump_json()
        for forbidden in ("SECRET RAW RESPONSE",attempts[0].response_text,"student-other"):
            self.assertNotIn(forbidden,serialized)
        self.assertIn("3 matched",serialized)
    def test_rejects_foreign_cluster(self):
        trend=score_divergence(history(),"s1","python.loops")
        c=MisconceptionCluster(student_id="student-other",skill_id="python.loops",concept_summary="private",evidence_attempt_ids=[],embedding_model_version="test")
        with self.assertRaises(ValueError): explain_flag(trend,verify_flag(trend),[c])
