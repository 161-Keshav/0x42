import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from tests.unit.helpers import history
from skill_erosion.logging_utils import configure_logging
from skill_erosion.agents.divergence_scoring.agent import score_divergence
class LoggingTests(unittest.TestCase):
    def test_stdout_shared_and_app_log_have_redacted_agent_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            capture=io.StringIO()
            with contextlib.redirect_stdout(capture):
                logger=configure_logging("teacher_dashboard",Path(tmp))
                score_divergence(history(),"s1","python.loops")
                for handler in logger.handlers: handler.flush()
                actual=(Path(tmp)/"logs/teacher_dashboard.log").read_text()
                shared=(Path(tmp)/"logs/skill_erosion.log").read_text()
                for text in (actual,shared,capture.getvalue()):
                    self.assertIn("agent=score_divergence",text)
                    self.assertIn("student_id=s1",text)
                    self.assertIn("status=widening",text)
                    self.assertIn("elapsed_ms=",text)
                    self.assertNotIn(history()[0].response_text,text)
                for handler in logger.handlers[:]: logger.removeHandler(handler); handler.close()
