import tempfile
import unittest
from pathlib import Path
from skill_erosion.contracts.models import MisconceptionCluster
from skill_erosion.embeddings.chroma import ChromaStore
from skill_erosion.agents.remediation.agent import recommend_remediation

class RemediationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.vectors=ChromaStore(Path(cls.tmp.name)/"chroma")
        cls.vectors.ensure_resources()
    @classmethod
    def tearDownClass(cls):
        cls.vectors.client.close()
        cls.tmp.cleanup()
    def cluster(self,summary="Python loop range upper endpoint is excluded; reason about the stopping boundary."):
        return MisconceptionCluster(student_id="s1",skill_id="python.loops",concept_summary=summary,evidence_attempt_ids=["a1@v1","a2@v1"],embedding_model_version="test")
    def test_semantic_resource_and_alternative(self):
        plan=recommend_remediation(self.cluster(),self.vectors)
        self.assertEqual(plan.status,"ready")
        self.assertTrue(plan.student_exercise)
        alternate=recommend_remediation(self.cluster(),self.vectors,plan.resource_ids)
        self.assertEqual(alternate.status,"ready")
        self.assertNotEqual(alternate.resource_ids,plan.resource_ids)
    def test_no_match_and_insufficient_evidence(self):
        all_ids=[r.resource_id for r in self.vectors.ensure_resources()]
        self.assertEqual(recommend_remediation(self.cluster(),self.vectors,all_ids).status,"no_matching_resource")
        self.assertEqual(recommend_remediation(self.cluster().model_copy(update={"evidence_attempt_ids":[]}),self.vectors).status,"insufficient_evidence")
        self.assertEqual(recommend_remediation(self.cluster("Medieval royal dynasties and genealogical succession"),self.vectors).status,"no_matching_resource")
