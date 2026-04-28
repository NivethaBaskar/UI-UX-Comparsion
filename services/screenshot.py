import os
import sys
import asyncio
from playwright.sync_api import sync_playwright

def capture_screenshot(url: str, output_path: str = "ui.png") -> str:
    """Captures a full page screenshot of the given URL."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.screenshot(path=output_path, full_page=True)
            return output_path
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            raise
        finally:
            browser.close()
