import base64
import io
import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from services.diff import generate_diff
from services.jira_service import JiraClient
from services.llm_analysis import analyze_differences
from services.screenshot import capture_screenshot
from services.ticket_intelligence import enrich_issues
from utils.image_utils import annotate_screenshot

try:
    from services.autogen_pipeline import AutoGenPipeline
    AUTOGEN_AVAILABLE = True
except ImportError:
    AUTOGEN_AVAILABLE = False

def _comparison_slider(img1_path: str, img2_path: str, label1: str, label2: str) -> None:
    """Render a drag-to-compare slider between two images using pure HTML/JS (no CDN)."""
    def _b64(path: str) -> str:
        img = Image.open(path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    src1, src2 = _b64(img1_path), _b64(img2_path)

    with Image.open(img1_path) as im:
        w, h = im.size
    height = int(h / w * 700) + 30  # match ~700px display width Streamlit uses

    html = """<!doctype html><html><head><style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0e1117}
#sc{position:relative;width:100%;overflow:hidden;cursor:ew-resize;user-select:none;-webkit-user-select:none}
#ib{display:block;width:100%;height:auto}
#fw{position:absolute;inset:0;overflow:hidden;clip-path:inset(0 50%% 0 0);pointer-events:none}
#ff{display:block;width:100%%;height:auto}
#dv{position:absolute;top:0;left:50%%;width:3px;height:100%%;background:rgba(255,255,255,.9);transform:translateX(-50%%);box-shadow:0 0 8px rgba(0,0,0,.6);pointer-events:none}
#hd{position:absolute;top:50%%;left:50%%;transform:translate(-50%%,-50%%);width:44px;height:44px;border-radius:50%%;background:#fff;box-shadow:0 2px 12px rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;font-size:22px;color:#333}
.lb{position:absolute;top:10px;background:rgba(0,0,0,.65);color:#fff;padding:4px 10px;border-radius:4px;font:13px/1.5 sans-serif;pointer-events:none;white-space:nowrap}
</style></head><body>
<div id="sc">
  <img id="ib" src="BACK_SRC">
  <div id="fw"><img id="ff" src="FRONT_SRC"></div>
  <div id="dv"><div id="hd">&#x21FA;</div></div>
  <span class="lb" style="left:10px">LABEL1</span>
  <span class="lb" style="right:10px">LABEL2</span>
</div>
<script>
(function(){
  var sc=document.getElementById('sc'),fw=document.getElementById('fw'),dv=document.getElementById('dv');
  var drag=false;
  function move(x){
    var r=sc.getBoundingClientRect();
    var p=Math.max(0,Math.min(100,(x-r.left)/r.width*100));
    fw.style.clipPath='inset(0 '+(100-p)+'%% 0 0)';
    dv.style.left=p+'%%';
  }
  sc.addEventListener('mousedown',function(e){drag=true;move(e.clientX);e.preventDefault();});
  window.addEventListener('mousemove',function(e){if(drag)move(e.clientX);});
  window.addEventListener('mouseup',function(){drag=false;});
  sc.addEventListener('touchstart',function(e){drag=true;move(e.touches[0].clientX);},{passive:true});
  window.addEventListener('touchmove',function(e){if(drag)move(e.touches[0].clientX);},{passive:true});
  window.addEventListener('touchend',function(){drag=false;});
})();
</script></body></html>"""

    html = (html
        .replace("BACK_SRC",  src2)
        .replace("FRONT_SRC", src1)
        .replace("LABEL1",    label1)
        .replace("LABEL2",    label2))

    components.html(html, height=height)


st.set_page_config(page_title="AI UI-UX Comparator", layout="wide")

BREAKPOINTS = {
    "Mobile (375px)":   {"width": 375,  "height": 812},
    "Tablet (768px)":   {"width": 768,  "height": 1024},
    "Desktop (1440px)": {"width": 1440, "height": 900},
}

SEV_COLORS = {
    "critical": "background-color:#ffb3b3;color:black",
    "high":     "background-color:#ffcccc;color:black",
    "medium":   "background-color:#fff3cc;color:black",
    "low":      "background-color:#ccffcc;color:black",
}

# ── Session state ────────────────────────────────────────────────────────────
for key, default in [
    ("comparison_done",    False),
    ("breakpoint_results", {}),
    ("figma_path",         None),
    ("live_url",           None),
    ("ticket_results",     None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("OpenAI Settings")
    api_key = st.text_input("API Key", type="password", key="openai_key")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    st.divider()
    st.subheader("Jira Configuration")
    jira_domain  = st.text_input("Domain",      placeholder="your-org.atlassian.net")
    jira_email   = st.text_input("Email")
    jira_token   = st.text_input("API Token",   type="password")
    jira_project = st.text_input("Project Key", placeholder="e.g. KAN")
    sev_threshold = st.selectbox(
        "Min severity to create ticket",
        ["critical", "high", "medium", "low"],
        index=3,
    )

    st.divider()
    st.subheader("Analysis Mode")
    if AUTOGEN_AVAILABLE:
        analysis_mode = st.radio(
            "Pipeline",
            ["Classic", "AutoGen (Multi-Agent)"],
            help=(
                "**Classic**: single GPT-4o call + enrichment.\n\n"
                "**AutoGen**: three-agent critique pipeline — "
                "AnalysisAgent → CritiqueAgent → SeverityAgent."
            ),
        )
    else:
        analysis_mode = "Classic"
        st.info("Install `pyautogen` to enable the multi-agent pipeline.")

# ── Header ───────────────────────────────────────────────────────────────────
st.title("AI UI-UX Comparison Tool")
st.markdown("Compare Figma designs with live URLs · detect differences · auto-generate Jira tickets.")

# ── Inputs ───────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.subheader("1. Upload Figma Design")
    figma_upload = st.file_uploader("PNG / JPG", type=["png", "jpg", "jpeg"])
with col2:
    st.subheader("2. Enter Live UI URL")
    live_url_input = st.text_input("Website URL", placeholder="https://example.com")

st.subheader("3. Select Breakpoints to Test")
selected_bp_labels = st.multiselect(
    "Viewport sizes",
    options=list(BREAKPOINTS.keys()),
    default=["Desktop (1440px)"],
)

# ── Compare ──────────────────────────────────────────────────────────────────
if st.button("Compare UI", type="primary", use_container_width=True):
    if not figma_upload:
        st.error("Please upload a Figma design image.")
    elif not live_url_input:
        st.error("Please enter a live URL.")
    elif not selected_bp_labels:
        st.error("Please select at least one breakpoint.")
    elif not os.environ.get("OPENAI_API_KEY"):
        st.error("Please provide an OpenAI API Key in the sidebar.")
    else:
        figma_path = "figma.png"
        with open(figma_path, "wb") as f:
            f.write(figma_upload.getbuffer())

        bp_results = {}
        total = len(selected_bp_labels)
        progress = st.progress(0, text="Starting…")

        for idx, bp_label in enumerate(selected_bp_labels):
            bp = BREAKPOINTS[bp_label]
            width, height = bp["width"], bp["height"]
            progress.progress(idx / total, text=f"Processing {bp_label}…")

            ui_path   = f"ui_{width}.png"
            diff_path = f"diff_{width}.png"

            try:
                capture_screenshot(live_url_input, ui_path, width, height)
                mismatch_pct = generate_diff(figma_path, ui_path, diff_path)

                conversation_log = []
                if analysis_mode == "AutoGen (Multi-Agent)":
                    pipeline = AutoGenPipeline(api_key=os.environ["OPENAI_API_KEY"])
                    enriched, conversation_log = pipeline.run(
                        figma_path, ui_path, diff_path, live_url_input, bp_label
                    )
                else:
                    raw_issues = analyze_differences(figma_path, ui_path, diff_path)
                    enriched   = enrich_issues(raw_issues, f"{live_url_input} [viewport: {bp_label}]")
                    for issue in enriched:
                        issue["breakpoint"] = bp_label

                annotated_path = f"annotated_{width}.png"
                try:
                    valid_for_annotation = [i for i in enriched if i.get("type") != "error"]
                    annotate_screenshot(ui_path, valid_for_annotation, annotated_path)
                except Exception:
                    annotated_path = ui_path

                bp_results[bp_label] = {
                    "mismatch_pct":     mismatch_pct,
                    "enriched":         enriched,
                    "ui_path":          ui_path,
                    "annotated_path":   annotated_path,
                    "diff_path":        diff_path,
                    "conversation_log": conversation_log,
                }
            except Exception as e:
                bp_results[bp_label] = {
                    "error":          str(e),
                    "mismatch_pct":   None,
                    "enriched":       [],
                    "ui_path":        None,
                    "annotated_path": None,
                    "diff_path":      None,
                }

        progress.progress(1.0, text="Done!")

        st.session_state.comparison_done    = True
        st.session_state.breakpoint_results = bp_results
        st.session_state.figma_path         = figma_path
        st.session_state.live_url           = live_url_input
        st.session_state.ticket_results     = None

        st.success(f"Comparison complete across {total} breakpoint(s)!")

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.comparison_done and st.session_state.breakpoint_results:
    bp_results = st.session_state.breakpoint_results
    figma_path = st.session_state.figma_path

    st.divider()
    st.subheader("Responsiveness Summary")

    # Mismatch % bar chart across breakpoints
    bp_labels   = list(bp_results.keys())
    mismatches  = [bp_results[bp].get("mismatch_pct") or 0 for bp in bp_labels]
    bar_colors  = ["#f44336" if m > 20 else "#ff9800" if m > 10 else "#4caf50" for m in mismatches]

    fig_summary = go.Figure(go.Bar(
        x=bp_labels,
        y=mismatches,
        marker_color=bar_colors,
        text=[f"{m:.1f}%" for m in mismatches],
        textposition="outside",
    ))
    fig_summary.update_layout(
        title="Pixel Mismatch % by Breakpoint",
        yaxis_title="Mismatch %",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig_summary, use_container_width=True)

    # ── Per-breakpoint tabs ──────────────────────────────────────────────────
    tabs = st.tabs(bp_labels)
    all_valid_issues = []

    for tab, bp_label in zip(tabs, bp_labels):
        result = bp_results[bp_label]
        with tab:
            if result.get("error"):
                st.error(f"Error: {result['error']}")
                continue

            st.metric("Pixel Mismatch", f"{result['mismatch_pct']:.2f}%")

            annotated = result.get("annotated_path") or result["ui_path"]
            _comparison_slider(figma_path, annotated, "Figma Design", f"Live UI ({bp_label})")
            with st.expander("Visual Diff", expanded=False):
                st.image(result["diff_path"], use_container_width=True)

            enriched     = result["enriched"]
            error_issues = [i for i in enriched if i.get("type") == "error"]
            valid_issues = [i for i in enriched if i.get("type") != "error"]

            for err in error_issues:
                st.error(f"AI Analysis Error: {err.get('issue', 'Unknown error')}")

            if not valid_issues and not error_issues:
                st.info("No issues detected at this breakpoint.")
            elif not valid_issues:
                st.warning("Analysis returned only errors — see details above. Download is still available below.")
            else:
                all_valid_issues.extend(valid_issues)

                sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
                for issue in valid_issues:
                    sev_counts[issue.get("severity", "low").lower()] = \
                        sev_counts.get(issue.get("severity", "low").lower(), 0) + 1

                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total",    len(valid_issues))
                m2.metric("Critical", sev_counts["critical"])
                m3.metric("High",     sev_counts["high"])
                m4.metric("Medium",   sev_counts["medium"])
                m5.metric("Low",      sev_counts["low"])

                df = pd.DataFrame(valid_issues)
                display_cols = [c for c in [
                    "jira_title", "component", "severity", "type",
                    "team", "root_cause", "suggested_fix",
                ] if c in df.columns]

                if "severity" in df.columns:
                    st.markdown(
                        df[display_cols].style.map(
                            lambda v: SEV_COLORS.get(str(v).lower(), ""),
                            subset=["severity"],
                        ).to_html(),
                        unsafe_allow_html=True,
                    )
                else:
                    st.dataframe(df[display_cols])

            # ── Download buttons — always shown after analysis ────────────────
            slug = bp_label.split()[0].lower()
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    label="Download Report (JSON)",
                    data=json.dumps(valid_issues, indent=2),
                    file_name=f"ui_issues_{slug}.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"json_{bp_label}",
                )
            with dl2:
                if valid_issues:
                    df_dl = pd.DataFrame(valid_issues)
                    display_cols_dl = [c for c in [
                        "jira_title", "component", "severity", "type",
                        "team", "root_cause", "suggested_fix",
                    ] if c in df_dl.columns]
                    buf = io.BytesIO()
                    df_dl[display_cols_dl].to_excel(buf, index=False, sheet_name="UI Issues")
                    excel_data = buf.getvalue()
                else:
                    buf = io.BytesIO()
                    pd.DataFrame().to_excel(buf, index=False, sheet_name="UI Issues")
                    excel_data = buf.getvalue()
                st.download_button(
                    label="Download Report (Excel)",
                    data=excel_data,
                    file_name=f"ui_issues_{slug}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"excel_{bp_label}",
                )

            # ── Agent conversation log (AutoGen mode only) ────────────────────
            logs = result.get("conversation_log", [])
            if logs:
                with st.expander("Agent Conversation Log", expanded=False):
                    AGENT_ICONS = {
                        "AnalysisAgent":  "🔍",
                        "CritiqueAgent":  "🧐",
                        "SeverityAgent":  "⚖️",
                    }
                    for entry in logs:
                        agent = entry["agent"]
                        icon  = AGENT_ICONS.get(agent, "🤖")
                        st.markdown(f"**{icon} {agent}**")
                        st.markdown(entry["content"])
                        st.divider()

    # ── Cross-breakpoint severity chart ──────────────────────────────────────
    if all_valid_issues:
        st.divider()
        st.subheader("Severity Distribution — All Breakpoints")

        total_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in all_valid_issues:
            k = issue.get("severity", "low").lower()
            total_sev[k] = total_sev.get(k, 0) + 1

        fig_sev = go.Figure(go.Bar(
            x=["Critical", "High", "Medium", "Low"],
            y=[total_sev["critical"], total_sev["high"], total_sev["medium"], total_sev["low"]],
            marker_color=["#d32f2f", "#f57c00", "#fbc02d", "#388e3c"],
        ))
        fig_sev.update_layout(
            yaxis_title="Count",
            height=280,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig_sev, use_container_width=True)

    # ── Jira section ─────────────────────────────────────────────────────────
    if all_valid_issues:
        st.divider()
        st.subheader("Jira Ticket Automation")

        jira_ready = all([jira_domain, jira_email, jira_token, jira_project])
        if not jira_ready:
            st.warning("Fill in all four Jira fields in the sidebar to enable ticket creation.")
        else:
            threshold_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            threshold_level = threshold_order.get(sev_threshold, 3)
            above_threshold = [
                i for i in all_valid_issues
                if threshold_order.get(i.get("severity", "low").lower(), 3) <= threshold_level
            ]
            st.info(
                f"{len(above_threshold)} of {len(all_valid_issues)} issues meet the "
                f"**{sev_threshold}** threshold across all breakpoints."
            )

            if st.button("Create Jira Tickets", type="primary"):
                with st.spinner("Creating Jira tickets…"):
                    all_ticket_results = []
                    try:
                        client = JiraClient(jira_domain, jira_email, jira_token, jira_project)
                        for bp_label, result in bp_results.items():
                            if result.get("error"):
                                continue
                            bp_valid = [i for i in result["enriched"] if i.get("type") != "error"]
                            if not bp_valid:
                                continue
                            results = client.create_tickets_for_issues(
                                bp_valid,
                                st.session_state.live_url,
                                figma_path,
                                result["ui_path"],
                                result["diff_path"],
                                sev_threshold,
                            )
                            all_ticket_results.extend(results)

                        st.session_state.ticket_results = all_ticket_results
                        created_count = sum(1 for r in all_ticket_results if r["status"] == "created")
                        st.success(f"{created_count} ticket(s) created.")
                    except Exception as e:
                        st.error(f"Jira error: {e}")

# ── Ticket dashboard ──────────────────────────────────────────────────────────
if st.session_state.ticket_results:
    results = st.session_state.ticket_results
    created = [r for r in results if r["status"] == "created"]
    skipped = [r for r in results if r["status"] == "skipped"]
    failed  = [r for r in results if r["status"] == "failed"]

    st.divider()
    st.subheader("Ticket Creation Dashboard")

    t1, t2, t3 = st.columns(3)
    t1.metric("Created",                   len(created))
    t2.metric("Skipped (below threshold)", len(skipped))
    t3.metric("Failed",                    len(failed))

    if created:
        st.markdown("**Created Tickets**")
        for r in created:
            issue = r["issue"]
            key   = r.get("ticket_key", "")
            url   = r.get("ticket_url", "#")
            sev   = issue.get("severity", "").upper()
            bp    = issue.get("breakpoint", "")
            st.markdown(
                f"- [{key}]({url}) · `{sev}` · `{bp}` — {issue.get('jira_title', issue.get('issue', ''))}"
            )

    if failed:
        st.markdown("**Failed Tickets**")
        for r in failed:
            st.error(f"{r['issue'].get('component', 'Unknown')}: {r.get('error', 'Unknown error')}")

    if skipped:
        with st.expander(f"Skipped ({len(skipped)}) — below severity threshold"):
            for r in skipped:
                issue = r["issue"]
                st.markdown(
                    f"- `{issue.get('severity','').upper()}` "
                    f"`{issue.get('breakpoint','')}` "
                    f"{issue.get('component','')} — {issue.get('issue','')}"
                )
