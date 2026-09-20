import os
import tempfile
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from skill_erosion.config import ROOT

class PortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); cls.prior=os.environ.get("SKILL_EROSION_DATA_DIR")
        os.environ["SKILL_EROSION_DATA_DIR"]=cls.tmp.name
    @classmethod
    def tearDownClass(cls):
        from skill_erosion.ui import get_runtime
        get_runtime(cls.tmp.name).vectors.client.close();get_runtime.clear()
        import logging
        logger=logging.getLogger("skill_erosion")
        for handler in logger.handlers[:]: logger.removeHandler(handler);handler.close()
        cls.tmp.cleanup()
        if cls.prior is None: os.environ.pop("SKILL_EROSION_DATA_DIR",None)
        else: os.environ["SKILL_EROSION_DATA_DIR"]=cls.prior
    def app(self,name):
        app=AppTest.from_file(str(ROOT/f"apps/{name}/app.py"),default_timeout=45).run()
        self.assertFalse(app.exception)
        return app
    def test_all_teacher_student_parent_controls(self):
        teacher=self.app("teacher_dashboard")
        teacher.button(key="load_data").click().run()
        teacher.selectbox(key="student").select("S-W001").run()
        teacher.selectbox(key="skill").select("python.loops").run()
        teacher.button(key="run_analysis").click().run()
        self.assertFalse(teacher.exception)
        self.assertEqual(teacher.session_state["journey"].trend.status,"widening")
        from skill_erosion.ui import get_runtime
        repo=get_runtime(self.tmp.name).repo
        original=repo.history("S-W001","python.loops")[0]
        repo.store([original.model_copy(update={"version":2,"hint_count":4})])
        teacher.run()
        self.assertFalse(teacher.exception)
        teacher.radio(key="decision").set_value("intervene").run()
        teacher.button(key="save_decision").click().run()
        teacher.button(key="refresh_cohort").click().run()
        self.assertFalse(teacher.exception)
        self.assertGreater(len(teacher.session_state["cohort"]),0)
        for decision in ("monitor","dismiss","intervene"):
            teacher.radio(key="decision").set_value(decision).run()
            teacher.button(key="save_decision").click().run()
            self.assertEqual(repo.get_decision("S-W001","python.loops"),decision)
            self.assertFalse(teacher.exception)
            if decision=="dismiss": self.assertEqual(teacher.session_state["journey"].remediation,[])
        self.assertEqual(len(teacher.get("download_button")),1)
        student=self.app("student_portal")
        student.button(key="load_data").click().run()
        student.selectbox(key="student").select("S-W001").run()
        student.selectbox(key="skill").select("python.loops").run()
        student.button(key="request_practice").click().run()
        self.assertFalse(student.exception)
        self.assertTrue(student.session_state["shown_plan"].resource_ids)
        first=student.session_state["shown_plan"].resource_ids
        student.button(key="alternative").click().run()
        self.assertNotEqual(first,student.session_state["shown_plan"].resource_ids)
        student.button(key="request_checkin").click().run()
        student.slider(key="self_confidence").set_value(.8)
        for i,answer in enumerate(("2, 3, 4","4","5")): student.radio(key=f"answer_{i}").set_value(answer)
        student.button(key="FormSubmitter:retest-Submit independent retest").click().run()
        self.assertFalse(student.exception)
        self.assertEqual(student.session_state["retest_result"]["independent_score"],1)
        self.assertIsNone(student.session_state["retest_result"]["gap_change"])
        parent=self.app("parent_portal")
        parent.selectbox(key="parent_account").select("parent-S-W001").run()
        parent.button(key="view_update").click().run()
        self.assertEqual(len(parent.text_input),1)
        self.assertEqual(len(parent.selectbox),1)
        parent.text_input(key="question").set_value("How can I help with practice?")
        parent.button(key="FormSubmitter:parent_question-Ask").click().run()
        self.assertFalse(parent.exception)
        self.assertIn("brief",parent.session_state["parent_answer"])
        parent.text_input(key="question").set_value("How is learning progressing?")
        parent.button(key="FormSubmitter:parent_question-Ask").click().run()
        self.assertIn("moving further apart",parent.session_state["parent_answer"])
        parent.selectbox(key="parent_account").select("parent-S-N001").run()
        self.assertNotIn("parent_answer",parent.session_state)
        parent.button(key="view_update").click().run()
        self.assertEqual(parent.session_state["parent_journey"].trend.student_id,"S-N001")
        from skill_erosion.ui import get_runtime
        pipeline=get_runtime(self.tmp.name)
        self.assertEqual(len(pipeline.repo.checkin_queue()),1)
        self.assertEqual(len([a for a in pipeline.repo.history("S-W001","python.loops") if a.origin=="follow_up"]),3)
