import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from skill_erosion.config import ROOT,load_taxonomy
from skill_erosion.data import read_attempts
from skill_erosion.storage.sqlite_repo import SQLiteRepository
from skill_erosion.agents.trace_collector.agent import collect_traces
from skill_erosion.agents.divergence_scoring.agent import score_divergence
from skill_erosion.metrics import calculate_metrics
from skill_erosion.assessments import submit_retest,QUESTIONS
class SyntheticTests(unittest.TestCase):
    def test_expanded_expected_scenarios_csv_json_and_transfer(self):
        rows=read_attempts(ROOT/"data/synthetic/attempts.json")
        self.assertEqual(len(rows),1200)
        expected=json.loads((ROOT/"data/synthetic/expected_trends.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            repo=SQLiteRepository(Path(tmp)/"db")
            self.assertEqual(collect_traces(rows,repo,load_taxonomy()).stored_versions,1200)
            self.assertEqual(collect_traces(read_attempts(ROOT/"data/synthetic/attempts.csv"),repo,load_taxonomy()).stored_versions,0)
            for item in expected:
                trend=score_divergence(repo.history(item["student_id"],item["skill_id"]),item["student_id"],item["skill_id"])
                self.assertEqual(trend.status,item["status"],item)
            self.assertEqual(calculate_metrics(repo.history("S-N001","python.loops"),"python.iteration",repo.history("S-N001","python.iteration"))["cross_skill_transfer"],"positive_transfer")
    def test_retest_and_checkin_do_not_invent_a_paired_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=SQLiteRepository(Path(tmp)/"db")
            collect_traces(read_attempts(ROOT/"data/synthetic/attempts.json"),repo,load_taxonomy())
            before=repo.count_versions()
            repo.request_checkin("S-W001","python.loops")
            self.assertEqual(repo.count_versions(),before)
            with self.assertRaises(ValueError): submit_retest(repo,"S-W001","python.loops",[None]*3)
            result=submit_retest(repo,"S-W001","python.loops",[q[1][q[2]] for q in QUESTIONS["python.loops"]])
            self.assertEqual(result["independent_score"],1)
            self.assertIsNone(result["gap_change"])
            self.assertEqual(repo.count_versions(),before+3)
            self.assertEqual(len(score_divergence(repo.history("S-W001","python.loops"),"S-W001","python.loops").checkpoints),5)
    def test_expansion_preserves_baseline_and_strengthens_visible_trajectory_separation(self):
        from scripts.generate_synthetic import generate,summary
        before,before_expected=generate(200)
        after,after_expected=generate(1200)
        self.assertEqual(after[:200],before)
        old=summary(before,before_expected); new=summary(after,after_expected)
        self.assertGreater(new["widening_narrowing_trajectory_separation"],old["widening_narrowing_trajectory_separation"])
        self.assertEqual(set(new["category_counts"].values()),{240})
