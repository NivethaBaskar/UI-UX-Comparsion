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

## Installation & Setup

### Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10 + | https://python.org |
| Node.js | 18 + | https://nodejs.org |
| Git | any | https://git-scm.com |
| OpenAI API Key | — | https://platform.openai.com |

---

### 1 — Clone the repository

```bash
git clone https://github.com/NivethaBaskar/UI-UX-Comparsion.git
cd UI-UX-Comparsion/ui-ux-comparator
```

---

### 2 — Python environment

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

---

### 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

---

### 4 — Install Playwright browser

```bash
python -m playwright install chromium
```

> Playwright drives a headless Chromium browser to capture live screenshots.

---

### 5 — Run the app

**Option A — Streamlit (quickest, no backend needed)**

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.  
Enter your OpenAI API Key in the sidebar and you're ready.

---

**Option B — React UI + FastAPI backend (full interface)**

Terminal 1 — start the FastAPI backend:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Terminal 2 — start the React frontend:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

### 6 — (Optional) Jira integration

In the sidebar / config panel, fill in:

| Field | Where to find it |
|-------|-----------------|
| Jira Domain | `your-org.atlassian.net` |
| Email | Your Atlassian account email |
| API Token | https://id.atlassian.com/manage-profile/security/api-tokens |
| Project Key | The short key shown in your Jira project (e.g. `KAN`) |

---

### Troubleshooting

| Issue | Fix |
|-------|-----|
| `playwright install` fails | Run `python -m playwright install-deps` first (Linux only) |
| `ModuleNotFoundError` | Make sure your venv is activated before running pip install |
| Screenshot is blank | The target URL may block headless browsers — try a different site |
| Streamlit port in use | Run `streamlit run app.py --server.port 8502` |
| React dev server CORS error | Ensure the FastAPI backend is running on port 8000 |

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
