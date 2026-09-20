import tempfile
import unittest
from pathlib import Path
from tests.unit.helpers import history
from skill_erosion.config import load_taxonomy
from skill_erosion.agents.trace_collector.agent import collect_traces
from skill_erosion.storage.sqlite_repo import SQLiteRepository
from skill_erosion.embeddings.chroma import ChromaStore
from skill_erosion.orchestration.pipeline import Pipeline
class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.repo=SQLiteRepository(root/"db.sqlite"); self.vectors=ChromaStore(root/"chroma")
        collect_traces(history((.3,.5,.7)),self.repo,load_taxonomy())
        self.pipeline=Pipeline(self.repo,self.vectors)
    def tearDown(self): self.vectors.client.close(); self.tmp.cleanup()
    def test_journey_persistence_and_human_gate(self):
        journey=self.pipeline.run("s1","python.loops")
        self.assertEqual(journey.trend.status,"widening")
        self.assertEqual(journey.verification.verdict,"confirmed")
        self.assertGreater(len(journey.clusters),0)
        self.assertEqual(journey.remediation[0].status,"ready")
        self.assertEqual(self.pipeline.student_plans(journey),[])
        self.repo.set_decision("s1","python.loops","intervene")
        self.assertEqual(self.pipeline.student_plans(journey)[0].status,"ready")
        self.repo.set_decision("s1","python.loops","dismiss")
        self.assertEqual(self.pipeline.student_plans(journey),[])
        self.assertEqual(self.pipeline.run("s1","python.loops").remediation,[])
        with self.repo.connection() as db: self.assertEqual(db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0],2)
        self.assertEqual(self.vectors.counts(),{"skill-erosion-attempts":6,"skill-erosion-resources":8})
    def test_unknown_and_parent_scope_refused(self):
        with self.assertRaises(ValueError): self.pipeline.run("missing","python.loops")
        self.repo.link_parent("p1","s1")
        with self.assertRaises(PermissionError): self.pipeline.for_parent("p1","python.loops",requested_student_id="other")
        self.assertEqual(self.pipeline.for_parent("p1","python.loops").trend.student_id,"s1")
    def test_alternative_follows_the_first_ready_plan_cluster(self):
        from skill_erosion.contracts.models import RemediationPlan
        journey=self.pipeline.run("s1","python.loops")
        unrelated=journey.clusters[0].model_copy(update={"concept_summary":"Medieval royal dynasties and genealogical succession"})
        journey=journey.model_copy(update={"clusters":[unrelated]+journey.clusters,"remediation":[RemediationPlan(status="no_matching_resource")]+journey.remediation})
        self.repo.set_decision("s1","python.loops","intervene")
        alternative=self.pipeline.alternative(journey,journey.remediation[1].resource_ids)
        self.assertEqual(alternative.status,"ready")
        self.assertNotEqual(alternative.resource_ids,journey.remediation[1].resource_ids)
