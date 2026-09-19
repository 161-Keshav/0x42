"""Render matching PNG/SVG architecture diagrams. Requires the diagrams extra."""

from html import escape
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/diagrams"
W, H = 1800, 1420
BG, INK, MUTED = "#F5F7FA", "#172B42", "#516379"
TEAL, BLUE, LINE = "#167A71", "#3863A5", "#B9C7D5"
im = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(im)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>Skill Erosion Tracker - target architecture</title>',
       '<desc>Two user interfaces and CSV JSON input connect to an orchestrator. Four FastMCP agents share versioned traces, embeddings, and curated resources. These are planned integrations.</desc>',
       f'<rect width="{W}" height="{H}" fill="{BG}"/>']


def font(size, bold=False):
    candidates = [
        Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu") / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def rect(x, y, w, h, fill="#FFFFFF", stroke=LINE, radius=16):
    draw.rounded_rectangle((x, y, x+w, y+h), radius=radius, fill=fill, outline=stroke, width=2)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')


def text(x, y, content, size=24, color=INK, bold=False):
    draw.text((x, y), content, font=font(size, bold), fill=color, anchor="lt")
    svg.append(f'<text x="{x}" y="{y+size*0.82}" font-family="Segoe UI,DejaVu Sans,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(content)}</text>')


def arrow(points, color=BLUE, both=False):
    draw.line(points, fill=color, width=3, joint="curve")
    svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" fill="none" stroke="{color}" stroke-width="3"/>')
    ends = [(points[-2], points[-1])]
    if both:
        ends.append((points[1], points[0]))
    for (ax, ay), (bx, by) in ends:
        a = math.atan2(by-ay, bx-ax)
        triangle = [(bx, by), (bx-13*math.cos(a-0.5), by-13*math.sin(a-0.5)), (bx-13*math.cos(a+0.5), by-13*math.sin(a+0.5))]
        draw.polygon(triangle, fill=color)
        svg.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in triangle)}" fill="{color}"/>')


def card(x, y, w, h, tag, title, lines, accent=TEAL):
    rect(x, y, w, h)
    text(x+24, y+22, tag, 18, accent, True)
    text(x+24, y+56, title, 27, INK, True)
    for i, line in enumerate(lines):
        text(x+24, y+102+i*31, line, 22, MUTED)


text(60, 43, "SKILL EROSION TRACKER", 19, TEAL, True)
text(60, 82, "Four agents. One longitudinal learning record.", 43, INK, True)
text(60, 142, "Target architecture from the submitted proposal  |  Starter interfaces exist; integrations remain to implement.", 23, MUTED)

card(60, 210, 530, 184, "TEACHER VIEW", "Trends and intervention summary", ["Assisted vs. unassisted performance", "Evidence sufficiency and skill history"])
card(635, 210, 530, 184, "STUDENT VIEW", "Targeted practice and resources", ["An exercise for the specific misconception", "Follow-up attempt at the next checkpoint"])
card(1210, 210, 530, 184, "PILOT INPUT", "CSV / JSON submission history", ["Code, written responses, quiz attempts", "Skill, time, task set, assistance condition"], BLUE)

arrow([(325, 394), (325, 468)], both=True)
arrow([(900, 394), (900, 468)], both=True)
arrow([(1475, 394), (1475, 468)])
text(355, 420, "Requests / results", 18, BLUE)
text(930, 420, "Requests / results", 18, BLUE)
text(1502, 420, "Normalize input", 18, BLUE)

rect(60, 470, 1680, 118, "#E8F1F8", "#A5BCD4")
text(88, 493, "ORCHESTRATION LAYER", 18, BLUE, True)
text(88, 530, "MCP client  /  tool sequencing  /  typed results  /  partial failures and sparse evidence", 29, INK, True)
arrow([(900, 588), (900, 650)], both=True)
text(926, 609, "Tool calls / results", 19, BLUE)

rect(60, 650, 1680, 294, "#EAF4F1", "#9CC3B9")
text(85, 674, "FASTMCP SERVER  /  FOUR INDEPENDENTLY CALLABLE TOOLS", 20, TEAL, True)
positions = [85, 505, 925, 1345]
card(positions[0], 720, 370, 178, "01  TRACE COLLECTOR", "Validate and version", ["Normalize and persist attempts", "Attach metadata and embeddings"])
card(positions[1], 720, 370, 178, "02  DIVERGENCE SCORER", "Measure the gap", ["Matched checkpoint pairs", "Structured features + ensemble"])
card(positions[2], 720, 370, 178, "03  MISCONCEPTION CLUSTERER", "Find recurring concepts", ["Semantic groups of weak work", "Retain attempt evidence"])
card(positions[3], 720, 370, 178, "04  REMEDIATION AGENT", "Retrieve a next step", ["RAG for the specific cluster", "Teacher + student outputs"])
for x in [455, 875, 1295]:
    arrow([(x, 808), (x+50, 808)], TEAL)
text(85, 915, "Arrows show the initial execution sequence. Agents share scoped history; each remains separately testable.", 18, TEAL)

# Shared dependency routes. Arrows point from agent layer to its state/provider.
arrow([(270, 944), (270, 1020)], TEAL)
arrow([(690, 944), (690, 976), (410, 976), (410, 1020)], TEAL)
arrow([(1110, 944), (1110, 988), (900, 988), (900, 1020)], TEAL)
arrow([(1530, 944), (1530, 1020)], TEAL)
# Dependency lines connect the agent layer to the shared state below.

card(60, 1020, 530, 203, "CANONICAL HISTORY", "Versioned trace store", ["SQLite: attempts and immutable revisions", "Scores, features and evidence provenance", "Planned adapter; durable source of truth"], BLUE)
card(635, 1020, 530, 203, "SEMANTIC MEMORY", "Sentence encoder + Chroma", ["Attempt embeddings and scoped metadata", "Student / skill / version / model filters", "Collector writes; clusterer queries"], BLUE)
card(1210, 1020, 530, 203, "REMEDIATION KNOWLEDGE", "Small curated resource library", ["Concept-specific explanations + exercises", "Separate resource embedding collection", "Return resource IDs with suggestions"], BLUE)

rect(60, 1270, 1680, 94, "#172B42", "#172B42")
text(88, 1291, "PILOT GUARDRAILS", 18, "#A7DED2", True)
text(88, 1324, "3+ paired checkpoints for a trend  |  Explicit insufficient-data state  |  Synthetic samples  |  No raw submission text in logs", 23, "#FFFFFF")
text(60, 1384, "Streamlit and SQLite are starter choices. FastMCP, semantic memory, four agents, and separate audiences come from the proposal.", 18, MUTED)

OUT.mkdir(parents=True, exist_ok=True)
im.save(OUT / "architecture.png")
svg.append("</svg>")
(OUT / "architecture.svg").write_text("\n".join(svg), encoding="utf-8")
print(f"Rendered {OUT / 'architecture.png'} and architecture.svg")
