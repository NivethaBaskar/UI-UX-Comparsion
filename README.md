# AI UI-UX Comparison Tool

An end-to-end tool to visually compare Figma designs against live website URLs. It captures live screenshots using Playwright, generates a visual diff, and uses an LLM (OpenAI GPT-4o) to analyze the differences and structure them into a tabular report.

## Features
- Upload a Figma design image.
- Capture live UI screenshots using Playwright.
- Generate visual difference images using `pixelmatch`.
- AI analysis of spacing, alignment, fonts, and colors.
- Downloadable structured JSON report.

## Setup Instructions

1. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   python -m pip install -r requirements.txt
   ```

3. **Install Playwright Browsers**
   ```bash
   python -m playwright install chromium
   ```

4. **Run the Streamlit App**
   ```bash
   cd ui-ux-comparator
   python -m streamlit run app.py
   ```

5. **Usage**
   - Open the app in your browser (usually `http://localhost:8501`).
   - Enter your OpenAI API Key in the sidebar.
   - Upload a Figma design (PNG/JPG).
   - Enter the live URL to compare against.
   - Click "Compare UI".
