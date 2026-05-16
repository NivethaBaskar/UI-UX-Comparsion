import streamlit as st
import os
import json
import pandas as pd
import plotly.graph_objects as go
from services.screenshot import capture_screenshot
from services.diff import generate_diff
from services.llm_analysis import analyze_differences
from services.ticket_intelligence import enrich_issues
from services.jira_service import JiraClient

st.set_page_config(page_title="AI UI-UX Comparator", layout="wide")

# ── Session state init ──────────────────────────────────────────────────────
for key, default in [
    ("comparison_done", False),
    ("enriched_issues", []),
    ("figma_path", None),
    ("ui_path", None),
    ("diff_path", None),
    ("mismatch_pct", None),
    ("live_url", None),
    ("ticket_results", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("OpenAI Settings")
    api_key = st.text_input("API Key", type="password", key="openai_key")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    st.divider()
    st.subheader("Jira Configuration")
    jira_domain    = st.text_input("Domain", placeholder="your-org.atlassian.net")
    jira_email     = st.text_input("Email")
    jira_token     = st.text_input("API Token", type="password")
    jira_project   = st.text_input("Project Key", placeholder="e.g. UIQA")
    sev_threshold  = st.selectbox(
        "Min severity to create ticket",
        ["critical", "high", "medium", "low"],
        index=3,
    )

# ── Header ──────────────────────────────────────────────────────────────────
st.title("AI UI-UX Comparison Tool")
st.markdown("Compare Figma designs with live URLs · detect differences · auto-generate Jira tickets.")

# ── Inputs ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.subheader("1. Upload Figma Design")
    figma_upload = st.file_uploader("PNG / JPG", type=["png", "jpg", "jpeg"])
with col2:
    st.subheader("2. Enter Live UI URL")
    live_url = st.text_input("Website URL", placeholder="https://example.com")

# ── Compare button ───────────────────────────────────────────────────────────
if st.button("Compare UI", type="primary", use_container_width=True):
    if not figma_upload:
        st.error("Please upload a Figma design image.")
    elif not live_url:
        st.error("Please enter a live URL.")
    elif not os.environ.get("OPENAI_API_KEY"):
        st.error("Please provide an OpenAI API Key in the sidebar.")
    else:
        with st.spinner("Processing comparison — this may take a minute…"):
            figma_path = "figma.png"
            with open(figma_path, "wb") as f:
                f.write(figma_upload.getbuffer())
            try:
                st.info("Capturing live screenshot…")
                ui_path = capture_screenshot(live_url, "ui.png")

                st.info("Generating pixel diff…")
                diff_path = "diff.png"
                mismatch_pct = generate_diff(figma_path, ui_path, diff_path)

                st.info("Analyzing differences with AI…")
                raw_issues = analyze_differences(figma_path, ui_path, diff_path)

                st.info("Enriching issues — grouping, root-cause analysis, team assignment…")
                enriched = enrich_issues(raw_issues, live_url)

                st.session_state.comparison_done  = True
                st.session_state.enriched_issues  = enriched
                st.session_state.figma_path       = figma_path
                st.session_state.ui_path          = ui_path
                st.session_state.diff_path        = diff_path
                st.session_state.mismatch_pct     = mismatch_pct
                st.session_state.live_url         = live_url
                st.session_state.ticket_results   = None

                st.success("Comparison complete!")
            except Exception as e:
                st.error(f"Error: {e}")

# ── Results ──────────────────────────────────────────────────────────────────
if st.session_state.comparison_done:
    st.divider()
    st.subheader(f"Pixel Mismatch: {st.session_state.mismatch_pct:.2f}%")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.image(st.session_state.figma_path, caption="Figma Design",       use_container_width=True)
    with c2:
        st.image(st.session_state.ui_path,    caption="Live UI Screenshot",  use_container_width=True)
    with c3:
        st.image(st.session_state.diff_path,  caption="Visual Diff",         use_container_width=True)

    enriched = st.session_state.enriched_issues
    error_issues = [i for i in enriched if i.get("type") == "error"]
    valid_issues  = [i for i in enriched if i.get("type") != "error"]

    for err in error_issues:
        st.error(f"AI Analysis Error: {err.get('issue', 'Unknown error')}")

    if not valid_issues and not error_issues:
        st.info("No issues detected — the live UI matches the Figma design.")
    elif not valid_issues:
        pass  # errors already displayed above
    else:
        st.divider()

        # ── Issue dashboard metrics ──────────────────────────────────────────
        sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in valid_issues:
            sev = issue.get("severity", "low").lower()
            sev_counts[sev] = sev_counts.get(sev, 0) + 1

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Issues", len(valid_issues))
        m2.metric("Critical",     sev_counts["critical"])
        m3.metric("High",         sev_counts["high"])
        m4.metric("Medium",       sev_counts["medium"])
        m5.metric("Low",          sev_counts["low"])

        # Severity distribution bar chart
        fig = go.Figure(go.Bar(
            x=["Critical", "High", "Medium", "Low"],
            y=[sev_counts["critical"], sev_counts["high"], sev_counts["medium"], sev_counts["low"]],
            marker_color=["#d32f2f", "#f57c00", "#fbc02d", "#388e3c"],
        ))
        fig.update_layout(
            title="Severity Distribution",
            xaxis_title="Severity",
            yaxis_title="Count",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Issues table ─────────────────────────────────────────────────────
        st.subheader("Detected Issues")
        df = pd.DataFrame(valid_issues)
        display_cols = [c for c in [
            "jira_title", "component", "severity", "type",
            "team", "confidence", "root_cause", "suggested_fix",
        ] if c in df.columns]

        SEV_COLORS = {
            "critical": "background-color:#ffb3b3;color:black",
            "high":     "background-color:#ffcccc;color:black",
            "medium":   "background-color:#fff3cc;color:black",
            "low":      "background-color:#ccffcc;color:black",
        }

        def highlight_sev(val):
            return SEV_COLORS.get(str(val).lower(), "")

        if "severity" in df.columns:
            st.markdown(
                df[display_cols].style.map(highlight_sev, subset=["severity"]).to_html(),
                unsafe_allow_html=True,
            )
        else:
            st.dataframe(df[display_cols])

        dl_col1, dl_col2 = st.columns(2)

        with dl_col1:
            st.download_button(
                label="Download Report (JSON)",
                data=json.dumps(valid_issues, indent=2),
                file_name="ui_issues_report.json",
                mime="application/json",
                use_container_width=True,
            )

        with dl_col2:
            import io
            excel_buf = io.BytesIO()
            df[display_cols].to_excel(excel_buf, index=False, sheet_name="UI Issues")
            st.download_button(
                label="Download Report (Excel)",
                data=excel_buf.getvalue(),
                file_name="ui_issues_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        # ── Jira ticket automation ────────────────────────────────────────────
        st.divider()
        st.subheader("Jira Ticket Automation")

        jira_ready = all([jira_domain, jira_email, jira_token, jira_project])
        if not jira_ready:
            st.warning("Fill in all four Jira fields in the sidebar to enable ticket creation.")
        else:
            threshold_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            threshold_level = threshold_order.get(sev_threshold, 3)
            tickets_to_create = [
                i for i in valid_issues
                if threshold_order.get(i.get("severity", "low").lower(), 3) <= threshold_level
            ]
            st.info(
                f"{len(tickets_to_create)} of {len(valid_issues)} issues meet the "
                f"**{sev_threshold}** threshold and will be sent to Jira."
            )

            if st.button("Create Jira Tickets", type="primary"):
                with st.spinner("Creating Jira tickets…"):
                    try:
                        client = JiraClient(jira_domain, jira_email, jira_token, jira_project)
                        results = client.create_tickets_for_issues(
                            valid_issues,
                            st.session_state.live_url,
                            st.session_state.figma_path,
                            st.session_state.ui_path,
                            st.session_state.diff_path,
                            sev_threshold,
                        )
                        st.session_state.ticket_results = results
                        created_count = sum(1 for r in results if r["status"] == "created")
                        st.success(f"{created_count} ticket(s) created successfully.")
                    except Exception as e:
                        st.error(f"Jira error: {e}")

# ── Ticket results dashboard ─────────────────────────────────────────────────
if st.session_state.ticket_results:
    results = st.session_state.ticket_results
    created = [r for r in results if r["status"] == "created"]
    skipped = [r for r in results if r["status"] == "skipped"]
    failed  = [r for r in results if r["status"] == "failed"]

    st.divider()
    st.subheader("Ticket Creation Dashboard")

    t1, t2, t3 = st.columns(3)
    t1.metric("Created",                len(created))
    t2.metric("Skipped (below threshold)", len(skipped))
    t3.metric("Failed",                 len(failed))

    if created:
        st.markdown("**Created Tickets**")
        for r in created:
            issue = r["issue"]
            key   = r.get("ticket_key", "")
            url   = r.get("ticket_url", "#")
            sev   = issue.get("severity", "").upper()
            comp  = issue.get("component", "")
            st.markdown(f"- [{key}]({url}) · `{sev}` · **{comp}** — {issue.get('jira_title', issue.get('issue', ''))}")

    if failed:
        st.markdown("**Failed Tickets**")
        for r in failed:
            comp = r["issue"].get("component", "Unknown")
            st.error(f"{comp}: {r.get('error', 'Unknown error')}")

    if skipped:
        with st.expander(f"Skipped ({len(skipped)}) — below severity threshold"):
            for r in skipped:
                issue = r["issue"]
                st.markdown(f"- `{issue.get('severity','').upper()}` {issue.get('component','')} — {issue.get('issue','')}")
