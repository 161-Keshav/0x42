"""Shared presentation and native controls for the three GapTrace workspaces."""
import base64
import logging
from html import escape
from pathlib import Path

import streamlit as st
from skill_erosion.config import ROOT, data_dir, load_taxonomy, skill_map
from skill_erosion.runtime import create_pipeline
from skill_erosion.data import read_attempts
from skill_erosion.agents.trace_collector.agent import collect_traces
from skill_erosion.agents.divergence_scoring.agent import score_divergence
from skill_erosion.agents.verification.agent import verify_flag

ASSETS = Path(__file__).parent / "assets"


@st.cache_resource
def get_runtime(root):
    return create_pipeline(Path(root))


@st.cache_data
def theme_css(theme_version):
    font = base64.b64encode((ASSETS / "Manrope.ttf").read_bytes()).decode("ascii")
    return ('@font-face {font-family:"Manrope";font-style:normal;font-weight:200 800;'
            'font-display:swap;src:url(data:font/ttf;base64,' + font + ') format("truetype");}\n'
            + (ASSETS / "theme.css").read_text(encoding="utf-8"))


def html(content):
    """All data interpolated by presentation helpers is escaped at its boundary."""
    st.html(content)


def shell(audience):
    from skill_erosion.logging_utils import configure_logging
    configure_logging({"Teacher": "teacher_dashboard", "Student": "student_portal", "Parent": "parent_portal"}[audience])
    st.set_page_config(page_title=f"GapTrace | {audience}", page_icon=":material/auto_stories:",
                       layout="wide", initial_sidebar_state="auto")
    st.html("<style>" + theme_css((ASSETS / "theme.css").stat().st_mtime_ns) + "</style>")
    with st.sidebar:
        html('<div class="sidebar-intro"><div class="brand">gaptrace<span> /</span></div>'
             f'<div class="workspace-name">{escape(audience)} workspace</div></div>')
    return get_runtime(str(data_dir()))


def page_header(audience, title, description):
    anchor = {"Teacher": "learning-in-perspective", "Student": "make-the-next-step-your-own",
              "Parent": "a-little-context-a-helpful-conversation"}[audience]
    html(f'<header class="page-heading"><div class="page-context"><strong>{escape(audience)} workspace</strong>'
         '<span>Learning, with context</span></div>'
         f'<h1 id="{anchor}">{escape(title)}</h1><p>{escape(description)}</p></header>')


def scope_heading(student, skill):
    html(f'<p class="scope-title">{escape(student)}</p>'
         f'<p class="scope-subtitle">{escape(skill_map()[skill]["name"])}</p>')


def note(title, body):
    html(f'<div class="sidebar-note"><strong>{escape(title)}</strong>{escape(body)}</div>')


def empty_state(title, description, details=()):
    cells = "".join(f'<span><strong>{escape(str(value))}</strong>{escape(label)}</span>' for label, value in details)
    html(f'<section class="empty-panel"><h3>{escape(title)}</h3><p>{escape(description)}</p>'
         + (f'<div class="empty-details">{cells}</div>' if cells else "") + '</section>')


def seed(pipeline):
    result = collect_traces(read_attempts(ROOT / "data/synthetic/attempts.json"), pipeline.repo, load_taxonomy())
    for student in pipeline.repo.students():
        pipeline.repo.link_parent("parent-" + student, student)
    return result


def import_real_data(pipeline, records):
    """Real classroom data goes through the exact same validated path as the
    synthetic seed: collect_traces() -> repo.store(). A record here lands in
    the same 'attempts' table as synthetic rows, so it shows up everywhere a
    student's history is read from (teacher dashboard, cohort view, parent
    portal) rather than only existing as a downloaded file."""
    import json
    payload = json.loads(records)
    rows = payload if isinstance(payload, list) else [payload]
    for row in rows:
        row["synthetic"] = False
    result = collect_traces(rows, pipeline.repo, load_taxonomy())
    for student in {r["student_id"] for r in rows}:
        try:
            pipeline.repo.link_parent("parent-" + student, student)
        except ValueError:
            pass  # already linked to a different account id; leave it alone
    return result


def load_control(pipeline):
    with st.sidebar:
        with st.expander("Demo data", expanded=False):
            st.caption("Synthetic learning histories for exploring the pilot.")
            if st.button("Load / refresh synthetic data", key="load_data", width="stretch"):
                result = seed(pipeline)
                st.success(f"{result.stored_versions} new versions stored. Existing records are kept.")
        with st.expander("Import real data", expanded=False):
            st.caption("Upload real assessment records (JSON, same shape as data/synthetic/attempts.json). "
                       "They are validated and stored in the same database as everything else, not just downloaded.")
            upload = st.file_uploader("Attempt records (.json)", type=["json"], key="real_data_upload")
            if upload is not None and st.button("Store uploaded records", key="store_real_data", width="stretch"):
                try:
                    result = import_real_data(pipeline, upload.getvalue().decode("utf-8"))
                    st.success(f"{result.stored_versions} new versions stored from the upload.")
                except Exception as exc:
                    error(exc)


def select_scope(pipeline):
    students = pipeline.repo.students()
    if not students:
        st.info("Open Demo data in the sidebar and load the synthetic dataset to explore the learning histories.")
        st.stop()
    with st.sidebar:
        student = st.selectbox("Student", students, key="student")
        skills = sorted({a.skill_id for a in pipeline.repo.history(student)})
        skill = st.selectbox("Skill", skills, format_func=lambda x: skill_map()[x]["name"], key="skill")
        note("A learning conversation", "Patterns help you choose a next step. They are not a diagnosis or a judgment.")
        note("Synthetic pilot", "Practice history is sample data. Personal check-in requests are stored separately.")
    reset_context((student, skill))
    return student, skill


def reset_context(context):
    if st.session_state.get("context") != context:
        for key in ("journey", "shown_plan", "excluded_resources", "retest_result", "parent_answer",
                    "parent_journey", "decision", "quiz_started", "self_confidence", "question"):
            st.session_state.pop(key, None)
        # Widget-bound input state is not covered by the fixed key list above:
        # the retest quiz uses one "answer_<i>" key per question, and Streamlit
        # keeps a widget's value under its key across reruns even when the
        # student/account changes. Without this, switching students/accounts
        # left the previous student's quiz answers pre-filled.
        for key in [k for k in st.session_state if k.startswith("answer_")]:
            st.session_state.pop(key, None)
        st.session_state["context"] = context


def error(exc):
    logging.getLogger("skill_erosion").error("ui operation failed error_type=%s", type(exc).__name__)
    st.error(f"This operation could not finish ({type(exc).__name__}). Check the local logs. "
             "The first semantic search needs internet access to download the local embedding model; retry after it is available.")


def trend_facts(trend):
    cp = trend.checkpoints
    tone = "tone-caution" if trend.status == "widening" else "tone-positive" if trend.status == "narrowing" else ""
    gap = f"{cp[-1].gap * 100:.1f} pp" if cp else "Not available"
    html('<dl class="facts">'
         f'<div><dt>Learning gap</dt><dd class="trend-value {tone}">{escape(trend.status.replace("_", " ").title())}</dd>'
         '<small>Across matched checkpoints</small></div>'
         f'<div><dt>Latest gap</dt><dd>{gap}</dd><small>Assisted minus independent</small></div>'
         f'<div><dt>Evidence history</dt><dd>{len(cp)}</dd><small>Matched checkpoints</small></div></dl>')


def performance_chart(checkpoints):
    rows = [{"Checkpoint": c.checkpoint_id, "order": i, "Assisted": c.assisted_score,
             "Independent": c.unassisted_score, "Gap (pp)": c.gap * 100, "Date": c.timestamp[:10]}
            for i, c in enumerate(checkpoints)]
    html('<div class="chart-legend" aria-label="Chart legend">'
         '<span><i></i>Independent</span><span><i class="assisted"></i>Assisted</span>'
         '<span><i class="gap"></i>Learning gap</span></div>')
    tooltip = [{"field": "Checkpoint", "type": "nominal"}, {"field": "Date", "type": "nominal"},
               {"field": "Independent", "type": "quantitative", "format": ".0%"},
               {"field": "Assisted", "type": "quantitative", "format": ".0%"},
               {"field": "Gap (pp)", "type": "quantitative", "format": ".1f"}]
    spec = {
        "height": 265,
        "encoding": {"x": {"field": "Checkpoint", "type": "ordinal",
                          "sort": {"field": "order"}, "axis": {"title": None, "labelAngle": 0, "labelPadding": 12,
                                   "labelExpr": "replace(datum.label, 'checkpoint-', 'C')", "labelLimit": 65, "labelOverlap": "greedy"}}},
        "layer": [
            {"mark": {"type": "area", "color": "#e1eee8", "opacity": .8},
             "encoding": {"y": {"field": "Assisted", "type": "quantitative", "scale": {"domain": [0, 1]},
                                "axis": {"title": "Score", "format": ".0%", "values": [0, .25, .5, .75, 1]}},
                          "y2": {"field": "Independent"}, "tooltip": tooltip}},
            {"mark": {"type": "line", "color": "#708398", "strokeWidth": 2, "strokeDash": [6, 4],
                      "point": {"filled": True, "size": 48, "color": "#708398"}},
             "encoding": {"y": {"field": "Assisted", "type": "quantitative"}, "tooltip": tooltip}},
            {"mark": {"type": "line", "color": "#176b58", "strokeWidth": 3,
                      "point": {"filled": True, "size": 64, "color": "#176b58"}},
             "encoding": {"y": {"field": "Independent", "type": "quantitative"}, "tooltip": tooltip}},
        ],
        "config": {"background": "transparent", "view": {"stroke": None},
                   "axis": {"domain": False, "ticks": False, "gridColor": "#e8eeea", "gridDash": [3, 4],
                            "labelColor": "#5e7067", "titleColor": "#5e7067", "titleFontWeight": 400,
                            "labelFont": "Manrope", "titleFont": "Manrope", "labelFontSize": 11, "titlePadding": 12}}
    }
    st.vega_lite_chart(rows, spec, width="stretch", theme=None)


def compact_chart(rows, field, title, domain=None, percent=True):
    y = {"field": field, "type": "quantitative", "title": None if percent else "Percentage points",
         "axis": {"format": ".0%" if percent else ".1f", "tickCount": 3}}
    if domain is not None:
        y["scale"] = {"domain": domain}
    st.vega_lite_chart(rows, {
        "height": 120, "mark": {"type": "line", "color": "#176b58", "strokeWidth": 2,
                                "point": {"filled": True, "size": 35, "color": "#176b58"}},
        "encoding": {"x": {"field": "Checkpoint", "type": "ordinal", "sort": {"field": "order"},
                          "axis": {"title": None, "labelAngle": 0, "labelFontSize": 10,
                                   "labelExpr": "replace(datum.label, 'checkpoint-', 'C')", "labelLimit": 45, "labelOverlap": "greedy"}},
                     "y": y, "tooltip": [{"field": "Checkpoint", "type": "nominal"},
                                        {"field": field, "type": "quantitative", "format": ".0%" if percent else ".1f", "title": title}]},
        "config": {"background": "transparent", "view": {"stroke": None},
                   "axis": {"domain": False, "ticks": False, "gridColor": "#e8eeea",
                            "labelColor": "#5e7067", "labelFont": "Manrope"}}
    }, width="stretch", theme=None)


def evidence_review(verification):
    html(f'<p class="review-verdict"><strong>{escape(verification.verdict.title())}</strong>'
         f' / {escape(verification.confidence.title())} evidence confidence</p>'
         '<ul class="evidence-list">' + "".join(f'<li>{escape(r)}</li>' for r in verification.reasons) + '</ul>')


def signal_grid(metrics):
    descriptions = {
        "hint_dependency_ratio": "Attempts that used a hint",
        "retention_decay": "Change between independent follow-ups",
        "error_pattern_diversity": "Distinct patterns among incorrect responses",
        "repeated_error_ratio": "Most frequent incorrect-response pattern",
        "confidence_calibration": "Confidence compared with observed results",
        "cross_skill_transfer": "Co-movement across related skills",
    }
    cells = []
    for key, value in metrics.items():
        if value is None or value == "insufficient_data":
            display = "More evidence needed"
        elif isinstance(value, (int, float)):
            display = f"{value * 100:+.1f} pp" if key == "retention_decay" else f"{value:.0%}"
        else:
            display = str(value).replace("_", " ").capitalize()
        cells.append(f'<div><dt>{escape(key.replace("_", " ").capitalize())}</dt><dd>{escape(display)}</dd>'
                     f'<small>{escape(descriptions.get(key, ""))}</small></div>')
    html('<dl class="learning-signals">' + "".join(cells) + '</dl>')


def cohort_rows(pipeline):
    rows = []
    for sid in pipeline.repo.students():
        for skill in sorted({a.skill_id for a in pipeline.repo.history(sid)}):
            trend = score_divergence(pipeline.repo.history(sid, skill), sid, skill)
            verification = verify_flag(trend)
            rows.append(dict(student=sid, skill=skill, trend=trend.status, verdict=verification.verdict,
                             confidence=verification.confidence, calibration=pipeline.metrics(sid, skill)["confidence_calibration"]))
    return rows


def _capability_chart_png(rows):
    """A plain Pillow bar chart: one bar per skill, height = latest independent
    score. No matplotlib dependency, just drawing primitives."""
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont
    width, height, margin = 640, 320, 56
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(ASSETS / "Manrope.ttf"), 14)
        font_small = ImageFont.truetype(str(ASSETS / "Manrope.ttf"), 11)
    except Exception:
        font = font_small = ImageFont.load_default()
    plot_h = height - margin - 40
    draw.line([(margin, height - margin), (width - 20, height - margin)], fill="#c9d6cf", width=1)
    n = max(len(rows), 1)
    bar_w = (width - margin - 40) / n
    for i, row in enumerate(rows):
        score = row["latest_independent_score"] if row["latest_independent_score"] is not None else 0
        x0 = margin + i * bar_w + bar_w * .18
        x1 = margin + i * bar_w + bar_w * .82
        y1 = height - margin
        y0 = y1 - plot_h * max(0, min(1, score))
        color = "#176b58" if row["trend"] != "widening" else "#b3542e"
        draw.rectangle([x0, y0, x1, y1], fill=color)
        draw.text(((x0 + x1) / 2, y1 + 6), row["skill_name"][:14], font=font_small, fill="#3c4a42", anchor="mt")
        draw.text(((x0 + x1) / 2, y0 - 4), f"{score:.0%}", font=font_small, fill="#3c4a42", anchor="mb")
    draw.text((margin, 12), "Latest independent score by skill", font=font, fill="#1c2620")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def capability_report_pdf(pipeline, student, decisions_by_skill=None):
    """One PDF: a plain-language overview of every skill this student has
    history for, plus a bar chart. This is what the 'Download full capability
    report' button in the parent portal produces."""
    from io import BytesIO
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    skills = sorted({a.skill_id for a in pipeline.repo.history(student)})
    rows = []
    for skill_id in skills:
        history = pipeline.repo.history(student, skill_id)
        trend = score_divergence(history, student, skill_id)
        independent = [a for a in history if a.assistance == "unassisted"]
        latest = independent[-1].correctness if independent else None
        rows.append(dict(skill_id=skill_id, skill_name=skill_map()[skill_id]["name"],
                          trend=trend.status, latest_independent_score=latest,
                          checkpoints=len(trend.checkpoints)))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, topMargin=.75 * inch, bottomMargin=.75 * inch)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"GapTrace — Learning Capability Overview", styles["Title"]),
             Paragraph(f"Student: {student}", styles["Normal"]), Spacer(1, 4),
             Paragraph("A plain-language summary of independent-practice patterns across skills. "
                       "This describes patterns over time, not a diagnosis or a ranking.", styles["Normal"]),
             Spacer(1, 16)]
    if rows:
        story.append(Image(BytesIO(_capability_chart_png(rows)), width=6.2 * inch, height=3.1 * inch))
        story.append(Spacer(1, 16))
        table_data = [["Skill", "Pattern", "Checkpoints", "Latest independent score"]]
        for r in rows:
            score = f"{r['latest_independent_score']:.0%}" if r["latest_independent_score"] is not None else "—"
            decision = (decisions_by_skill or {}).get(r["skill_id"])
            table_data.append([r["skill_name"], r["trend"].replace("_", " ").title(), str(r["checkpoints"]), score])
        table = Table(table_data, colWidths=[1.8 * inch, 1.6 * inch, 1.1 * inch, 1.7 * inch])
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176b58")),
                                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                    ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#c9d6cf")),
                                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7f4")])]))
        story.append(table)
    else:
        story.append(Paragraph("No learning history is available yet.", styles["Normal"]))
    doc.build(story)
    return buf.getvalue()


def summary_text(journey, metrics, decision):
    t = journey.trend
    e = journey.explanation
    lines = ["GapTrace student learning summary", f"Student: {t.student_id}", f"Skill: {t.skill_id}", f"Trend: {t.status}",
             f"Teacher decision: {decision or 'awaiting review'}", e.headline, e.explanation, *e.evidence_points,
             e.next_step, "Learning signals:"]
    lines += [f"{key}: {value if value is not None else 'insufficient_data'}" for key, value in metrics.items()]
    return "\n".join(lines)
