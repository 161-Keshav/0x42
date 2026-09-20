"""Exercise a real Streamlit teacher journey and parent question; retain evidence."""
import json
import logging
from streamlit.testing.v1 import AppTest
from skill_erosion.config import ROOT,data_dir

def main():
    teacher=AppTest.from_file(str(ROOT/"apps/teacher_dashboard/app.py"),default_timeout=60).run()
    teacher.button(key="load_data").click().run()
    teacher.selectbox(key="student").select("S-W001").run()
    teacher.selectbox(key="skill").select("python.loops").run()
    teacher.button(key="run_analysis").click().run()
    assert not teacher.exception,teacher.exception
    journey=teacher.session_state["journey"]
    print("TEACHER JOURNEY",journey.trend.status,journey.verification.verdict,len(journey.clusters),"clusters")
    print("TEACHER LOG FILE CONTENT")
    print((data_dir()/"logs/teacher_dashboard.log").read_text(encoding="utf-8"))
    parent=AppTest.from_file(str(ROOT/"apps/parent_portal/app.py"),default_timeout=60).run()
    parent.selectbox(key="parent_account").select("parent-S-W001").run()
    parent.button(key="view_update").click().run()
    assert len(parent.text_input)==1
    parent.text_input(key="question").set_value("How can I help with practice?")
    parent.button(key="FormSubmitter:parent_question-Ask").click().run()
    assert not parent.exception,parent.exception
    print("PARENT QUESTION INPUTS",len(parent.text_input))
    print("PARENT ANSWER",parent.session_state["parent_answer"])
    from skill_erosion.ui import get_runtime
    p=get_runtime(str(data_dir())); counts=p.vectors.counts()
    print("CHROMA COUNTS",json.dumps(counts))
    # Teacher analyzed loops, parent analyzed related iteration: 10 records each.
    assert counts=={"skill-erosion-attempts":20,"skill-erosion-resources":8},counts
    metrics=p.metrics("S-N001","python.loops")
    assert metrics["cross_skill_transfer"]=="positive_transfer"
    print("CALCULATE_METRICS RELATED SKILLS",json.dumps(metrics))
    (ROOT/"docs/verification/live-summary.json").write_text(json.dumps({"chroma_counts":counts,"transfer":metrics["cross_skill_transfer"],"parent_question_inputs":len(parent.text_input)},indent=2))
    p.vectors.client.close();get_runtime.clear()
    logger=logging.getLogger("skill_erosion")
    for h in logger.handlers[:]:logger.removeHandler(h);h.close()
    print("UI EVIDENCE VERIFIED")
if __name__=="__main__":
    import os
    import tempfile
    (ROOT/".build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT/".build") as isolated:
        os.environ["SKILL_EROSION_DATA_DIR"]=isolated
        main()
