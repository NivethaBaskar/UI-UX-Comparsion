import streamlit as st
import os
import json
import pandas as pd
from services.screenshot import capture_screenshot
from services.diff import generate_diff
from services.llm_analysis import analyze_differences

st.set_page_config(page_title="AI UI-UX Comparator", layout="wide")

st.title("🎨 AI UI-UX Comparison Tool")
st.markdown("Compare Figma designs with live URLs, detect differences, and generate an AI-powered issue report.")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API Key", type="password")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Figma Design")
    figma_upload = st.file_uploader("Upload Image (PNG/JPG)", type=["png", "jpg", "jpeg"])

with col2:
    st.subheader("2. Enter Live UI URL")
    live_url = st.text_input("Website URL", placeholder="https://example.com")

if st.button("Compare UI", type="primary", use_container_width=True):
    if not figma_upload:
        st.error("Please upload a Figma design image.")
    elif not live_url:
        st.error("Please enter a valid URL.")
    elif not os.environ.get("OPENAI_API_KEY"):
         st.error("Please provide an OpenAI API Key in the sidebar.")
    else:
        with st.spinner("Processing comparison... This may take a minute."):
            figma_path = "figma.png"
            with open(figma_path, "wb") as f:
                f.write(figma_upload.getbuffer())
            
            try:
                st.info("Capturing live screenshot...")
                ui_path = capture_screenshot(live_url, "ui.png")
                
                st.info("Generating pixel diff...")
                diff_path = "diff.png"
                mismatch_pct = generate_diff(figma_path, ui_path, diff_path)
                
                st.info("Analyzing differences with AI...")
                issues = analyze_differences(figma_path, ui_path, diff_path)
                
                st.success("Comparison Complete!")
                st.subheader(f"Mismatch Percentage: {mismatch_pct:.2f}%")
                
                img_col1, img_col2, img_col3 = st.columns(3)
                with img_col1:
                    st.image(figma_path, caption="Figma Design", use_container_width=True)
                with img_col2:
                    st.image(ui_path, caption="Live UI Screenshot", use_container_width=True)
                with img_col3:
                    st.image(diff_path, caption="Visual Diff", use_container_width=True)

                st.subheader("Detected Issues")
                if issues and not (len(issues) == 1 and issues[0].get("type") == "error"):
                    df = pd.DataFrame(issues)
                    
                    def highlight_severity(val):
                        if val == "high": return 'background-color: #ffcccc; color: black'
                        elif val == "medium": return 'background-color: #fff3cc; color: black'
                        elif val == "low": return 'background-color: #ccffcc; color: black'
                        return ''
                    
                    if "severity" in df.columns:
                         html_table = df.style.map(highlight_severity, subset=['severity']).to_html()
                    else:
                         html_table = df.to_html(classes='table table-bordered')
                    st.markdown(html_table, unsafe_allow_html=True)
                    
                    json_str = json.dumps(issues, indent=2)
                    st.download_button(
                        label="Download Issues Report (JSON)",
                        file_name="ui_issues_report.json",
                        mime="application/json",
                        data=json_str
                    )
                else:
                    if issues and issues[0].get("type") == "error":
                         st.error(issues[0].get("issue"))
                    else:
                         st.write("No major issues detected or failed to parse issues.")
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
