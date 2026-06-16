# Building an AI Deck Builder for Strategy & Analyst Teams
### A self-implementation guide — we build this ourselves (no off-the-shelf deck tool)

---

## Executive Summary

- **What we're building:** a system that auto-produces a *recurring* strategy deck — we start with the **Quarterly Business Review (QBR)**, the standard quarterly leadership review — from our own data, where every number is verified and the AI writes only the words around it.
- **The core rule:** verified data → AI writes narrative *around numbers it cannot change* → deterministic renderer formats it. The AI never invents a figure and never does layout.
- **Where numbers come from:** a governed **semantic layer** (our single source of truth), queried through an API — never the LLM guessing from raw tables. Next period's deck = the same query with a new date.
- **How we render:** one structured model, **two renderers** — **MARP first** (fast Markdown→PDF/HTML for drafting, web, and locked decks) and **python-pptx** (native, *editable* PowerPoint for board/exec decks).
- **Charts:** standard charts can be native+editable in PowerPoint; **waterfall and Mekko are not native anywhere**, so we render those as images (Plotly) and embed them — one code path that works in both renderers.
- **Text overflow** (the #1 rendering defect): defended in layers — length caps in the prompt → autofit on shrink → a **render-and-check QA gate**. Fit is a render-time fact, so we *verify* it, we don't guess.
- **Getting better over time:** reviewer feedback becomes durable **template rules**, so each period's first draft lands closer to final.
- **Where to start:** one deck, one company, end-to-end. The hard part is trustworthy, refreshable numbers — nail that before anything else.

---

## 1. What we're building, and the one idea that organizes it

We are building an **analyst-grade deck generator**, not a generic "make slides from a prompt" tool. The distinction matters because a strategy/research deck is a *data-provenance problem*: every figure must be defensible, traceable, and refreshable next period.

A presentation has three layers — **narrative** (what it argues), **design** (how it looks), and **data** (the numbers underneath). The data layer is our entire job. So our pipeline is:

> **A data pipeline produces verified numbers → the LLM writes narrative *around numbers it is not allowed to change* → deterministic renderers format it.**

The LLM never authors a figure and never does layout. That is the line between a tool an analyst trusts and one they re-check (re-checking is what kills adoption).

---

## 2. The recurring decks

| Deck | Full name | Audience | Cadence | Character |
|------|-----------|----------|---------|-----------|
| **MBR** | Monthly Business Review | Internal teams/leadership | Monthly | Operational pulse; metric-dense; tactical; lower polish |
| **QBR** | Quarterly Business Review | Internal leadership | Quarterly | Strategic step-back; performance vs plan; forecast; asks |
| **BOD** | Board of Directors deck | The board | Quarterly | Governance-level; financials, strategy, risks, decisions; highest polish |
| **OCEO** | Office of the CEO | CEO + chief-of-staff function | Ad hoc / recurring | Synthesis; all-hands, board prep, cross-company narratives |

**We start with the QBR.** Stable structure, fixed audience, recurring cadence, enough data density to prove the hard part. Once one recurring deck works end-to-end, every additional deck is cheap.

---

## 3. Architecture overview

```
  ┌─────────────┐   ┌──────────────────┐   ┌─────────────────┐
  │ Data sources│──▶│  Semantic /      │──▶│  Metric API     │
  │ (warehouse, │   │  metric layer    │   │ (governed       │
  │  CRM, finance)│  │ (single source   │   │  numbers only)  │
  └─────────────┘   │  of truth)       │   └────────┬────────┘
                    └──────────────────┘            │
                                                    ▼
                       ┌──────────────────────────────────────┐
                       │  Deck assembly                        │
                       │  Template schema  ◀── locked numbers  │
                       │        +                              │
                       │  Narrative LLM (writes around numbers,│
                       │  uses last period's deck for context) │
                       │        +                              │
                       │  Chart module (Plotly → PNG)          │
                       └───────────────────┬──────────────────┘
                                           ▼
                       ┌──────────────────────────────────────┐
                       │  ONE structured model (filled schema) │
                       └───────┬───────────────────────┬──────┘
                               ▼                       ▼
                   ┌────────────────────┐   ┌────────────────────┐
                   │ MARP renderer      │   │ python-pptx render │
                   │ → HTML / PDF       │   │ → editable .pptx   │
                   │ (fast, web, locked)│   │ (board/exec edits) │
                   └─────────┬──────────┘   └─────────┬──────────┘
                             └───────────┬────────────┘
                                         ▼
                       ┌──────────────────────────────────────┐
                       │  QA gate (render→image→inspect):      │
                       │  text overflow, unfilled {{slots}}    │
                       └───────────────────┬──────────────────┘
                                           ▼
                         Deck ──▶ feedback ──▶ TEMPLATE RULES
                                  (draft N+1 starts closer to final)
```

---

## 4. The five layers, in detail

### Layer 1 — Data & semantic layer (how data collection works)

**The rule: never let the LLM query raw tables.** That produces inconsistent, unverifiable numbers and the classic failure where sales, finance, and ops each arrive with a different "revenue."

We define each metric **once** in a semantic (metric) layer that becomes the single source of truth. The deck queries *governed metrics* through an API. This guarantees the QBR number equals the dashboard number, every time.

**How we build it, cheapest first:**
- **v0:** governed SQL **views** in our warehouse (Postgres / BigQuery / Snowflake). One reviewed, locked view per metric. Enough to start.
- **Proper semantic layer:** **Cube** (open-source `Cube Core`) or **dbt Semantic Layer / MetricFlow** if we already run dbt. Warehouse-native options exist too (Snowflake Semantic Views, Databricks Metric Views).
- These expose metrics over SQL / REST / GraphQL / MCP, so the pipeline pulls *defined* metrics rather than guessing.

**Metric definition (illustrative, Cube-style):**
```yaml
cubes:
  - name: revenue
    measures:
      - name: net_revenue
        sql: "{invoices.amount} - {credits.amount}"
        type: sum
        description: "Net recognized revenue (USD)"
      - name: nrr
        sql: "..."          # net revenue retention
        type: number
        description: "Net revenue retention, trailing 12mo"
    dimensions:
      - name: period
        sql: invoice_month
        type: time
```

**Refresh = re-run the query for the new period.** Define once; "next quarter's QBR" is the same query with a new date filter.

**Provenance:** store, with each pulled number, *where it came from* (source view + query + timestamp). That is what lets every figure trace to source on a board/research deck.

---

### Layer 2 — Template-as-schema

The deck is a **structured contract**, not a freeform prompt. Each section declares its purpose, the exact metrics it expects, and how it renders. The LLM fills the contract; it cannot invent sections or numbers.

**QBR template schema (illustrative):**
```yaml
deck: qbr
period: "{{ quarter }}"
sections:
  - id: exec_summary
    title: "Executive Summary"
    type: narrative
    inputs: [net_revenue, net_revenue_qoq, nrr, churn_rate]
    prompt: "3-4 bullet TL;DR of the quarter. Lead with the number, then the why."

  - id: scorecard
    title: "KPIs vs Target"
    type: metric_table
    inputs: [net_revenue, gross_margin, nrr, cac, churn_rate]
    show: [actual, target, delta, status]      # status = RAG color

  - id: segment_perf
    title: "Performance by Segment"
    type: chart
    chart: bar
    inputs: [net_revenue_by_segment]

  - id: initiatives
    title: "Strategic Initiatives — Status"
    type: narrative
    context: prior_deck            # pulls last quarter's commitments
    prompt: "For each initiative we committed to last quarter, state status and variance."

  - id: asks
    title: "Decisions Needed"
    type: narrative
    prompt: "List explicit asks/decisions for leadership."
```

`inputs` are metric names from Layer 1; the assembler resolves them to locked values before the LLM sees the slide. Each section also maps to a **named layout** used by both renderers.

---

### Layer 3 — Narrative generation

The LLM writes **commentary around locked numbers**, under two rules:

1. **Numbers are read-only.** Pass resolved metric values into the prompt as fixed facts: *use these verbatim; do not compute, estimate, or alter any figure.*
2. **Period-over-period continuity.** Feed last period's deck as context so the story connects ("last quarter we flagged churn; here's where it landed"). This is what makes it read like an analyst.

**Prompt skeleton:**
```
You are drafting the {{ section.title }} slide of a QBR.
LOCKED METRICS (use verbatim, do not change):
  net_revenue = $4.2M  (+12% QoQ)
  nrr = 108%
  churn_rate = 2.1%
LAST QUARTER'S COMMENTARY ON THIS SECTION:
  "{{ prior_deck.section.exec_summary }}"
TASK: {{ section.prompt }}
Constraints: ≤ 50 words per bullet. No new numbers beyond those above.
```

We use the Anthropic API (Claude), one scoped call per section — easier to control and cache. **The word caps here are also our first defense against text overflow** (Layer 4).

---

### Layer 4 — Rendering (dual: MARP first, then python-pptx)

**Principle: one structured model, two renderers.** Formatting stays out of the LLM. The LLM emits filled content (schema/JSON); each renderer turns it into slides deterministically. Adding or reordering a section changes one schema — not two renderers.

- **MARP renderer (build first):** emit Markdown from the model, render to HTML/PDF via the Marp CLI. Fast iteration, web distribution, and any deck that ships locked. This is where we prove the pipeline quickly.
  ```bash
  marp deck.md --pdf          # reliable
  marp deck.md --html         # web
  ```
- **python-pptx renderer (add second):** emit native `.pptx` from the *same* model into a corporate template — clone the template, populate named placeholders. For board/exec decks people hand-edit.
  ```python
  from pptx import Presentation
  from pptx.chart.data import CategoryChartData
  from pptx.enum.chart import XL_CHART_TYPE
  from pptx.util import Inches

  prs = Presentation("corporate_template.pptx")   # brand + layouts live here
  slide = prs.slides.add_slide(prs.slide_layouts[2])   # e.g. "Scorecard" layout
  slide.placeholders[0].text = "Executive Summary"
  slide.placeholders[1].text = exec_summary_text       # from Layer 3, length-capped

  # native, editable chart for the STANDARD types:
  data = CategoryChartData()
  data.categories = ["Enterprise", "Mid-Market", "SMB"]
  data.add_series("Net Revenue", (2.1, 1.4, 0.7))
  slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED,
                         Inches(1), Inches(2), Inches(8), Inches(4.5), data)
  prs.save("Q2_2026_QBR.pptx")
  ```

#### Chart strategy (shared across both renderers)

Why this needs its own strategy: MARP has **no native charts at all**, and python-pptx **cannot create the chart types finance decks need**:
- **Waterfall** — python-pptx doesn't support it. It's an Office-2016 `chartEx` type in an XML namespace (`cx:`) that python-pptx never adopted (the feature PR has sat open for years). python-pptx covers the *classic* set only (column, bar, line, pie, scatter, area…).
- **Mekko / Marimekko** — not a native chart type *anywhere*; it's a variable-width stacked bar (mosaic plot).

**Our default: render every chart to an image with one charting module (Plotly) and embed it.** One code path, identical visuals in MARP and pptx.
- Plotly does both hard cases: native `go.Waterfall`, and Mekko via custom-width `go.Bar` (`width` + `offset`). Export to PNG with kaleido, embed on the slide.
- Tradeoff: an embedded chart is a picture, not click-editable — almost always fine (no one hand-edits a waterfall's geometry).

**Optional upgrade, pptx renderer only:** render the *standard* charts (column/bar/line/pie) as native python-pptx charts so execs can edit them; keep waterfall/Mekko as images. If a waterfall *must* stay editable, the routes are **Spire.Presentation** (commercial Python lib that creates native waterfall + funnel in `.pptx`) or **chartEx XML injection** (build the waterfall once in PowerPoint, save as template, swap data via unpack→edit→repack).

#### Text-fit strategy

Root cause: **fit is a render-time computation** (font metrics + box size + wrap), resolved by the rendering engine. A generator that doesn't render can only *estimate*. So we defend in layers:
1. **Cap length in the Layer 3 prompts** — first and best defense; applies to both renderers.
2. **At render time:**
   - python-pptx: set `text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE` so PowerPoint shrinks gracefully on open; optionally call `fit_text()` for an approximate pre-shrink (needs the font file; not exact).
   - MARP: it's HTML/CSS, so text reflows; use CSS to scale or clip if a block runs long.
3. **Verify by rendering** — the only *true* check. Convert the built deck to images and inspect (below).

#### QA gate (both renderers)

Because content is machine-generated into fixed slots, render each build to images and inspect before shipping:
```bash
# .pptx → images (LibreOffice + Poppler); MARP already gives a PDF
soffice --headless --convert-to pdf Q2_2026_QBR.pptx
pdftoppm -jpeg -r 150 Q2_2026_QBR.pdf slide

# check for leftover/unfilled placeholders in extracted text
#   grep for {{ }}, XXXX, TODO, lorem, etc.
```
Check the images for text overflow, collisions, and unfilled `{{slots}}`. For an unattended "generate next quarter's deck" run, this gate is what stops a broken deck reaching a reviewer.

**Design note:** keep brand decisions in the template; vary layouts per section; avoid the AI tells (accent underbars beneath titles, identical layout on every slide, text-only slides). Our edge is the data, not the decoration — keep this light.

---

### Layer 5 — Feedback-to-rules loop

The biggest lever against rework: **capture revisions as durable rules, not one-off edits.**
- "Lead with the number, not the story" → encode in the section prompt.
- A section always gets reordered → change the schema.
- A metric is consistently reframed → fix its definition or label.
- A layout consistently overflows → tighten the prompt's word cap or adjust the placeholder.

Keep a `rules.yaml` per deck type that the assembler reads. Over a few cycles, draft N+1 starts much closer to final.

---

## 5. Tech stack

| Concern | v0 choice | Later |
|---|---|---|
| Orchestration | Python script | LangGraph / small workflow engine |
| Metric store | Governed SQL views | Cube Core or dbt Semantic Layer |
| Narrative | Claude API (scoped calls per section) | + caching, eval harness |
| Slot binding | Resolve metric names → locked values before render | `{metric.path}` DSL in placeholders |
| Charts | **Plotly → PNG (kaleido), embedded in both renderers** | native python-pptx charts for standard types |
| Render (fast/locked) | **MARP CLI → PDF/HTML** | themed brand CSS |
| Render (editable) | **python-pptx → corporate template `.pptx`** | richer layouts; Spire/XML for editable waterfall |
| Text fit | prompt caps + `TEXT_TO_FIT_SHAPE` + render-check | measured fit (Pillow `ImageFont`) where needed |
| QA | render→image, grep for unfilled slots + overflow check | automated visual-diff gate |
| Prior-deck context | filled schemas stored as JSON | versioned deck store |

Expect these dependencies: `python-pptx`, `plotly` + `kaleido`, the Anthropic SDK, the Marp CLI (Node), and LibreOffice + Poppler (`pdftoppm`) for QA renders.

---

## 6. Phased build plan

**Phase 0 — Prove the loop, MARP-first (1–2 weeks).**
One QBR, one company's data, hardcoded. Define ~8 metrics as SQL views. Write the QBR schema. Pull numbers → Claude writes narrative around locked numbers → charts as Plotly PNGs → **render with MARP to PDF** → run the QA image check. Goal: a trustworthy deck with zero invented figures, fast.

**Phase 1 — Add the editable PPTX renderer.**
Point the *same* structured model at python-pptx into a corporate template. Standard charts go native; waterfall/Mekko stay as images. Wire the text-fit handling.

**Phase 2 — Real data layer + refresh.**
Replace SQL views with Cube/dbt; wire connectors (warehouse, CRM, finance). "Next quarter's deck" becomes one command.

**Phase 3 — Continuity + more deck types.**
Add prior-deck context and the feedback-to-rules loop. Extend the schema + template approach to MBR and BOD.

**Phase 4 — Enterprise hardening.** See §7.

---

## 7. Enterprise hardening (later phases)

For deployment beyond our own walls:
- **SSO / SAML** and role-based access.
- **Permissions inherited from the semantic layer** — who can see which metric flows through to who can generate which deck.
- **Data handling** — PII controls; VPC / on-prem deployment or zero-data-retention so data never leaves the customer boundary.
- **Audit trails** — every figure traceable to source + timestamp; every deck reproducible.
- **Brand-compliance** — automated checks against the corporate template.

---

## 8. Scope discipline

The temptation is to generalize to "any deck." Don't. The advantage comes entirely from a *narrow, repeatable* target where we can wire the data tightly and tune the template:
- One deck type (QBR) before any other.
- One company's data end-to-end before multi-tenant.
- The data-provenance problem solved in one lane before breadth.
Generalizing early throws away the only moat we have — trustworthy, refreshable numbers.

---

## 9. Week one checklist

1. Pick the single QBR we'll target. Get a real example of last quarter's deck.
2. List the ~8–12 metrics it contains. Write one governed SQL view per metric.
3. Write the QBR schema (§4.2), mapping each section to a layout.
4. Wire one Claude call per section with locked-number, length-capped prompts (§4.3).
5. Render charts as Plotly PNGs; assemble and **render with MARP to PDF** (§4 Layer 4).
6. Run the QA image check; compare to the real deck.
7. Then: add the python-pptx renderer, and start replacing SQL views with a real semantic layer.

The hard part is trustworthy, refreshable numbers — nail that on one deck before touching anything else.
