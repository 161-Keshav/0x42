import tempfile
import unittest
from pathlib import Path
from pydantic import ValidationError
from tests.unit.helpers import record
from skill_erosion.contracts.models import Attempt
from skill_erosion.storage.sqlite_repo import SQLiteRepository
from skill_erosion.agents.trace_collector.agent import collect_traces
from skill_erosion.config import load_taxonomy

class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.repo=SQLiteRepository(Path(self.tmp.name)/"test.db")
    def tearDown(self): self.tmp.cleanup()
    def test_ingestion_is_idempotent(self):
        first=collect_traces([record()],self.repo,load_taxonomy())
        again=collect_traces([record()],self.repo,load_taxonomy())
        self.assertEqual((first.stored_versions,again.stored_versions,self.repo.count_versions()),(1,0,1))
    def test_versions_append_and_conflicts_are_atomic(self):
        collect_traces([record()],self.repo,load_taxonomy())
        with self.assertRaises(ValueError): collect_traces([record(9),record(correctness=.1)],self.repo,load_taxonomy())
        self.assertEqual(self.repo.count_versions(),1)
        collect_traces([record(version=2,correctness=.7)],self.repo,load_taxonomy())
        self.assertEqual(self.repo.history("s1","python.loops")[0].version,2)
        self.assertEqual(self.repo.count_versions(),2)
        with self.assertRaises(ValueError): collect_traces([record(version=4)],self.repo,load_taxonomy())
        with self.assertRaises(ValueError): collect_traces([record(version=3,student_id="s2")],self.repo,load_taxonomy())
    def test_invalid_records_rejected(self):
        for changes in ({"correctness":1.1},{"time_taken_seconds":-1},{"timestamp":"yesterday"},{"student_id":""},{"self_reported_confidence":-1}):
            with self.subTest(changes=changes),self.assertRaises(ValidationError): Attempt(**record(**changes))
        with self.assertRaises(ValueError): collect_traces([record(skill_id="unknown")],self.repo,load_taxonomy())
    def test_parent_backend_refuses_other_student(self):
        collect_traces([record(),record(2,student_id="s2")],self.repo,load_taxonomy())
        self.repo.link_parent("p1","s1")
        self.assertEqual(self.repo.get_linked_student("p1"),"s1")
        self.assertEqual({a.student_id for a in self.repo.history_for_parent("p1")},{"s1"})
        with self.assertRaises(PermissionError): self.repo.history_for_parent("p1","s2")
        with self.assertRaises(PermissionError): self.repo.get_linked_student("missing")
        with self.assertRaises(ValueError): self.repo.link_parent("p1","s2")
    def test_decisions_persist_and_invalid_values_fail(self):
        self.repo.set_decision("s1","python.loops","dismiss")
        self.assertEqual(SQLiteRepository(self.repo.path).get_decision("s1","python.loops"),"dismiss")
        with self.assertRaises(ValueError): self.repo.set_decision("s1","python.loops","punish")
