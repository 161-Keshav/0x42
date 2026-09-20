# GapTrace visual refinement implementation plan

> For agentic workers: execute inline using the executing-plans workflow, with browser inspection and regression checks between implementation and delivery.

**Goal:** Refine all three working portals into a coherent, calm learning workspace.
**Architecture:** Keep the three Streamlit applications, routes, widget keys and backend contracts. Share a local font, CSS tokens and escaped presentation helpers; render actual assessment data with native Vega-Lite charts. No new service or external font dependency at runtime.
**Tech stack:** Python, Streamlit 1.64, native Vega-Lite, locally bundled Manrope.
**Spec:** User's design-taste-frontend request and 13-one-shot-build-spec.md.

## Audit and design decision

Mode: redesign, preserve identity and information architecture. Existing forest-green gaptrace / wordmark, three audiences, tabs, forms and functional controls stay recognizable. Existing Segoe UI/Trebuchet typography, washed-out green canvas, oversized headings, decorative 0x42 caption, default blue notices and vertically stacked chart/table layout need refinement. No SEO migration: these are local applications with unchanged routes.

Reading this as: a learning workspace for teachers, students, and parents, with a calm, purposeful language, leaning toward a clean educational workbook.

The taste skill excludes dense dashboards. Apply its audit and visual principles contextually alongside the frontend-design skill, retaining Streamlit's native accessible forms and data-table patterns. No marketing hero, decorative photography or animation is appropriate here.

Dials: variance 4, motion 1, density 5. Preserve a light theme. Colors: forest #176B58, ink #20352F, muted #63736D, paper #FFFFFF, canvas #F5F7F6, border #DCE5E0. Reserved semantic amber for a widening gap; blue/gray supports chart distinction. Typography: locally bundled Manrope for interface/headings, existing monospace stack for data identifiers. Corners 8px for controls, 12px for grouped content.

Signature: an actual paired-performance chart, shading the distance between supported and independent work. Directly connected to GapTrace's purpose; no decorative metric fabrication.

## Tasks

- [x] Shared foundation: add licensed local font and CSS assets, revise shell and page-header helpers, use consistent focus states and mobile collapse. Preserve the wordmark.
- [x] Teacher composition: paired chart and factual overview beside an evidence/decision panel; secondary signals and checkpoint detail below. Keep all decision, refresh, download and evidence controls.
- [x] Student composition: focused practice content with a quieter support panel and clearly grouped retest questions. Keep reviewed-practice gating, alternatives and check-in behavior.
- [x] Parent composition: concise learning-update panel and a readable question form with exactly one text input, scoped to the linked learner.
- [x] Verify: run the existing integrated portal test; compile source and check protected starter files. Inspect real populated/empty views at desktop and mobile, check console errors and contrast. Run the full regression suite before delivery.

No backend scoring, assessment data, authentication scope or API-key behavior changes are part of this visual task. Visible copy retains its supportive voice. Replace decorative dashes and remove engineering metadata from primary reading flow. Escape all data rendered into HTML.


## Verified follow-up

Browser testing exposed a pre-existing multi-process Chroma conflict after retest writes. The launcher now owns one loopback service; clients verify a per-start identity token and fail closed on stale connections. Child processes receive an absolute data directory. Three real-service regressions cover new writes, outages, and port reuse across datasets. All scoring and assessment contracts remain unchanged.
