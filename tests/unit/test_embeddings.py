import tempfile
import unittest
from pathlib import Path
from tests.unit.helpers import record
from skill_erosion.contracts.models import Attempt
from skill_erosion.embeddings.chroma import ChromaStore
from skill_erosion.agents.misconception_clustering.agent import cluster_misconceptions

class EmbeddingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.vectors=ChromaStore(Path(cls.tmp.name)/"chroma")
    @classmethod
    def tearDownClass(cls):
        cls.vectors.client.close()
        cls.tmp.cleanup()
    def test_real_semantics_cluster_paraphrases_not_unrelated_answers(self):
        texts=["I thought range(1, 5) includes the upper endpoint, so the loop visits five.",
               "The ending boundary is counted in Python iteration; I expected range(1, 5) to reach five.",
               "The capital of France is Madrid.","Plants obtain energy from the moon instead of sunlight."]
        attempts=[Attempt(**record(i,assistance="unassisted",correctness=.2,response_text=t)) for i,t in enumerate(texts)]
        clusters=cluster_misconceptions(attempts,self.vectors,"s1","python.loops")
        self.assertEqual(len(clusters),1)
        self.assertEqual(set(clusters[0].evidence_attempt_ids),{"a0@v1","a1@v1"})
        self.assertIn("MiniLM",clusters[0].embedding_model_version)
        self.assertEqual(self.vectors.counts()["skill-erosion-attempts"],4)
    def test_scope_latest_version_and_minimum_repetition(self):
        attempts=[Attempt(**record(20,assistance="unassisted",correctness=.2)),Attempt(**record(21,student_id="other",assistance="unassisted",correctness=.2))]
        self.assertEqual(cluster_misconceptions(attempts,self.vectors,"s1","python.loops"),[])
        attempts.append(Attempt(**record(20,version=2,assistance="unassisted",correctness=1)))
        self.assertEqual(cluster_misconceptions(attempts,self.vectors,"s1","python.loops"),[])
