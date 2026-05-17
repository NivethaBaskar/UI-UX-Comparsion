# AI UI-UX Comparator

> **Paste a Figma design + a live URL — get annotated screenshots, pixel diffs, severity-ranked issues, and auto-generated Jira tickets in under 60 seconds.**

---

## What It Does

QA engineers spend hours manually comparing designs to live UIs. This tool eliminates that by running a fully automated pipeline:

1. **Screenshot** — Playwright captures the live site at Mobile, Tablet, and Desktop breakpoints
2. **Diff** — pixelmatch computes a pixel-level diff image highlighting every mismatch
3. **Analyze** — GPT-4o vision reads all three images and returns structured issues (spacing, alignment, fonts, colors, missing components) with severity and bounding boxes
4. **Annotate** — colored bounding boxes (red = critical, orange = high, amber = medium, green = low) are drawn directly on the live screenshot
5. **Enrich** — a second LLM pass deduplicates issues, adds root causes, suggested fixes, team ownership, and Jira-ready titles
6. **Ticket** — one click creates Jira tickets with ADF-formatted descriptions and attached diff images

## UI

Two interfaces — use whichever fits your workflow:

| Interface | How to run |
|-----------|-----------|
| **Streamlit** (quick demo) | `streamlit run app.py` |
| **React + FastAPI** (full UI) | `npm run dev` in `frontend/`, start FastAPI backend |

The React UI includes a **drag-to-compare slider** (Figma ↔ annotated live UI) and a classic side-by-side view — toggle between them per breakpoint.

## Setup

```bash
# 1. Python environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Dependencies
pip install -r requirements.txt
python -m playwright install chromium

# 3. Run Streamlit
streamlit run app.py

# 4. Or run React UI (separate terminal)
cd frontend && npm install && npm run dev
```

## Configuration

| Setting | Where |
|---------|-------|
| OpenAI API Key | Sidebar (Streamlit) or Config panel (React) |
| Jira domain / email / token / project | Sidebar → auto-creates tickets above your severity threshold |
| Analysis mode | Classic (single GPT-4o pass) or AutoGen (3-agent critique pipeline) |
| Breakpoints | Mobile 375px · Tablet 768px · Desktop 1440px |

## Tech Stack

- **Python** — Streamlit, Playwright, Pillow, pixelmatch, OpenAI SDK, pandas, Plotly
- **React** — TypeScript, Vite, Tailwind CSS
- **AI** — GPT-4o vision for analysis + enrichment; optional AutoGen multi-agent pipeline
- **Integrations** — Atlassian Jira REST API (ADF tickets with image attachments)

## Output

- Severity-ranked issue table (critical / high / medium / low) with root cause, suggested fix, team assignment, and confidence score
- Annotated screenshot with colored bounding boxes per issue
- Pixel diff image
- Downloadable JSON and Excel reports
- Jira tickets (optional)
