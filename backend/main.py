import os
import sys
import json
import time
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

app = FastAPI(title="UI-UX Comparator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BREAKPOINTS = {
    "Mobile (375px)":   (375,  812),
    "Tablet (768px)":   (768, 1024),
    "Desktop (1440px)": (1440,  900),
}
BP_SUFFIX = {
    "Mobile (375px)":   "375",
    "Tablet (768px)":   "768",
    "Desktop (1440px)": "1440",
}


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def log_sse(message: str, level: str = "info") -> str:
    return sse("log", {"message": message, "level": level, "ts": time.time()})


class CompareRequest(BaseModel):
    figma_path: str
    url: str
    breakpoints: list
    mode: str = "classic"
    api_key: str


@app.post("/api/upload")
async def upload_figma(file: UploadFile = File(...)):
    dest = BASE_DIR / "figma.png"
    content = await file.read()
    dest.write_bytes(content)
    return {"path": str(dest), "size": len(content)}


@app.post("/api/compare")
async def compare(req: CompareRequest):
    async def stream() -> AsyncGenerator[str, None]:
        loop = asyncio.get_event_loop()
        os.environ["OPENAI_API_KEY"] = req.api_key

        # --- Cleanup existing generated images ---
        yield log_sse("Deleting existing diff and UI PNG files before comparison...", "info")
        removed = 0
        for pattern in ["diff_*.png", "ui_*.png", "annotated_*.png"]:
            for f in BASE_DIR.glob(pattern):
                f.unlink(missing_ok=True)
                removed += 1
        yield log_sse(f"Cleaned up {removed} file(s)", "success")
        await asyncio.sleep(0)

        results: dict = {}
        all_conv_logs: list = []

        for bp_label in req.breakpoints:
            dims = BREAKPOINTS.get(bp_label, (1440, 900))
            suffix = BP_SUFFIX.get(bp_label, "1440")
            ui_path   = str(BASE_DIR / f"ui_{suffix}.png")
            diff_path = str(BASE_DIR / f"diff_{suffix}.png")
            figma_path = req.figma_path

            # --- Screenshot ---
            yield log_sse(f"[{bp_label}] Capturing screenshot at {dims[0]}x{dims[1]}px...", "info")
            try:
                from services.screenshot import capture_screenshot
                await loop.run_in_executor(
                    None, capture_screenshot, req.url, ui_path, dims[0], dims[1]
                )
                yield log_sse(f"[{bp_label}] Screenshot saved -> ui_{suffix}.png", "success")
            except Exception as e:
                yield log_sse(f"[{bp_label}] Screenshot failed: {e}", "error")
                yield sse("error", {"message": str(e)})
                return
            await asyncio.sleep(0)

            # --- Accessibility contrast check ---
            a11y_issues: list = []
            try:
                from services.accessibility import check_accessibility
                a11y_issues = await loop.run_in_executor(None, check_accessibility, ui_path)
                yield log_sse(
                    f"[{bp_label}] Accessibility check: {len(a11y_issues)} contrast issue(s) found",
                    "success" if not a11y_issues else "info",
                )
            except Exception as e:
                yield log_sse(f"[{bp_label}] Accessibility check skipped: {e}", "info")
            await asyncio.sleep(0)

            # --- Pixel diff ---
            yield log_sse(f"[{bp_label}] Generating pixel diff...", "info")
            mismatch_pct = 0.0
            try:
                from services.diff import generate_diff
                mismatch_pct = await loop.run_in_executor(
                    None, generate_diff, figma_path, ui_path, diff_path
                )
                yield log_sse(
                    f"[{bp_label}] Diff complete — {mismatch_pct:.2f}% mismatch", "success"
                )
            except Exception as e:
                yield log_sse(f"[{bp_label}] Diff generation failed: {e}", "error")
            await asyncio.sleep(0)

            # --- Analysis ---
            if req.mode == "autogen":
                yield log_sse(f"[{bp_label}] Starting 3-agent AutoGen pipeline...", "info")
                yield log_sse("  -> Agent 1: AnalysisAgent (GPT-4o vision)...", "agent")
                try:
                    from services.autogen_pipeline import AutoGenPipeline
                    pipeline = AutoGenPipeline(api_key=req.api_key)
                    final_issues, conv_log = await loop.run_in_executor(
                        None, pipeline.run,
                        figma_path, ui_path, diff_path, req.url, bp_label
                    )
                    for i, entry in enumerate(conv_log):
                        agent_name = entry.get("agent", "Agent")
                        agent_num  = i + 1
                        preview    = str(entry.get("content", ""))[:250].replace("\n", " ")
                        yield log_sse(
                            f"  -> Agent {agent_num} ({agent_name}): {preview}...", "agent"
                        )
                    all_conv_logs.extend(conv_log)
                    yield log_sse(
                        f"[{bp_label}] AutoGen complete — {len(final_issues)} issue(s)", "success"
                    )
                except Exception as e:
                    yield log_sse(f"[{bp_label}] AutoGen pipeline failed: {e}", "error")
                    final_issues = []
            else:
                yield log_sse(f"[{bp_label}] Running GPT-4o vision analysis...", "info")
                raw_issues: list = []
                try:
                    from services.llm_analysis import analyze_differences
                    raw_issues = await loop.run_in_executor(
                        None, analyze_differences, figma_path, ui_path, diff_path
                    )
                    yield log_sse(
                        f"[{bp_label}] Found {len(raw_issues)} raw issue(s)", "success"
                    )
                except Exception as e:
                    yield log_sse(f"[{bp_label}] Analysis failed: {e}", "error")
                await asyncio.sleep(0)

                yield log_sse(
                    f"[{bp_label}] Enriching issues (dedup + root cause + team)...", "info"
                )
                try:
                    from services.ticket_intelligence import enrich_issues
                    final_issues = await loop.run_in_executor(
                        None, enrich_issues, raw_issues, req.url
                    )
                    yield log_sse(
                        f"[{bp_label}] Enrichment done — {len(final_issues)} issue(s) after dedup",
                        "success",
                    )
                except Exception as e:
                    yield log_sse(f"[{bp_label}] Enrichment failed: {e}", "error")
                    final_issues = raw_issues
            await asyncio.sleep(0)

            # --- Annotate screenshot with bounding boxes ---
            annotated_path = str(BASE_DIR / f"annotated_{suffix}.png")
            try:
                from services.annotate import annotate_screenshot
                await loop.run_in_executor(
                    None, annotate_screenshot, ui_path, final_issues, annotated_path
                )
                yield log_sse(f"[{bp_label}] Annotated screenshot saved", "success")
            except Exception as e:
                yield log_sse(f"[{bp_label}] Annotation skipped: {e}", "info")
                annotated_path = ui_path  # fall back to plain screenshot
            await asyncio.sleep(0)

            results[bp_label] = {
                "issues":           final_issues,
                "a11y_issues":      a11y_issues,
                "mismatch_pct":     round(mismatch_pct, 2),
                "ui_image":         f"/api/images/ui_{suffix}.png",
                "annotated_image":  f"/api/images/annotated_{suffix}.png",
                "diff_image":       f"/api/images/diff_{suffix}.png",
                "figma_image":      "/api/images/figma.png",
            }

        yield log_sse("All breakpoints processed. Sending results...", "success")
        yield sse("result", {"breakpoints": results, "conversation_log": all_conv_logs})
        yield log_sse("Done.", "success")

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/images/{filename}")
async def serve_image(filename: str):
    path = BASE_DIR / filename
    if not path.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)
    return FileResponse(str(path))


@app.post("/api/create-tickets")
async def create_tickets(body: dict):
    try:
        from services.jira_service import JiraClient
        client = JiraClient(
            domain=body["jira_domain"],
            email=body["jira_email"],
            api_token=body["jira_token"],
            project_key=body["jira_project"],
        )
        suffix = body.get("suffix", "1440")
        ticket_results = client.create_tickets_for_issues(
            issues=body["issues"],
            url=body["url"],
            figma_path=str(BASE_DIR / "figma.png"),
            ui_path=str(BASE_DIR / f"ui_{suffix}.png"),
            diff_path=str(BASE_DIR / f"diff_{suffix}.png"),
            severity_threshold=body.get("severity_threshold", "medium"),
        )
        return {"results": ticket_results}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
