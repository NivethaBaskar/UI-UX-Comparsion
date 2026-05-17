"""
Multi-agent UI analysis pipeline — AutoGen concept, zero extra dependencies.

Implements the same three-agent critique architecture as AutoGen GroupChat
using direct OpenAI API calls.  Each agent is a stateless function with its
own system prompt; results are passed sequentially between agents.

Agent flow
----------
AnalysisAgent  →  CritiqueAgent  →  SeverityAgent
  (GPT-4o           (removes          (business-aware
 vision call)    false positives,     re-prioritises,
                 adds root cause,     adds confidence
                  team, jira_title)      score)
"""

import json
import re

from openai import OpenAI

from services.llm_analysis import analyze_differences


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> list:
    text = text.strip()
    text = re.sub(r"```(?:json)?\n?", "", text).strip("`").strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return []


def _call_agent(client: OpenAI, system_prompt: str, user_message: str) -> str:
    """Single-turn agent call — returns the assistant's raw text reply."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        max_tokens=2000,
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


# ── Agent system prompts ──────────────────────────────────────────────────────

_CRITIQUE_PROMPT = """You are a senior QA engineer reviewing a UI regression report.

Given a JSON list of detected UI issues you must:
1. Remove false positives or issues with vague / non-actionable descriptions.
2. Merge near-duplicate issues — keep the most descriptive version.
3. Add to every remaining issue:
   - "root_cause": most probable technical cause (CSS, missing token, JS error, asset, etc.)
   - "suggested_fix": one concise, actionable fix a developer can act on immediately.
   - "team": responsible team — one of: Frontend Platform, Design System, Checkout Team, Marketing, Auth Team, Mobile.
   - "jira_title": Jira ticket title in format "[SEVERITY] short description"
     e.g. "[HIGH] Navbar top padding 12 px off on mobile viewport"
4. Normalize severity to exactly one of: critical, high, medium, low.

Return ONLY a valid JSON array. No markdown fences. No commentary."""

_SEVERITY_PROMPT = """You are a product manager and accessibility expert finalising bug priorities.

Reclassify each issue's severity using these rules:
  critical  → checkout / payment flow broken, primary CTA invisible, form non-functional, WCAG AA failure.
  high      → navigation broken, hero text wrong, layout broken at this viewport.
  medium    → spacing / alignment off by > 8 px, wrong font size or weight, noticeable colour mismatch.
  low       → cosmetic only, < 4 px delta, subtle colour variation, hover state mismatch.

Add a "confidence" field (integer 0-100): your confidence this is a genuine regression vs. a test artefact.

Return ONLY the updated JSON array. No markdown. No commentary."""


# ── Pipeline ──────────────────────────────────────────────────────────────────

class AutoGenPipeline:
    """
    Three-agent critique pipeline for UI regression analysis.

    Uses the OpenAI SDK directly — no additional packages required.
    Each agent is invoked as a separate single-turn chat completion,
    mirroring AutoGen's sequential GroupChat handoff pattern.
    """

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def run(
        self,
        figma_path: str,
        ui_path: str,
        diff_path: str,
        url: str,
        bp_label: str,
    ) -> tuple[list, list]:
        """
        Run the full three-agent pipeline for one breakpoint.

        Returns
        -------
        enriched_issues : list
        conversation_log : list[dict]  — for display in Streamlit
        """
        conversation_log = []

        # ── Agent 1: AnalysisAgent ────────────────────────────────────────────
        raw_issues = analyze_differences(figma_path, ui_path, diff_path)

        error_issues = [i for i in raw_issues if i.get("type") == "error"]
        if error_issues:
            return raw_issues, conversation_log

        conversation_log.append({
            "agent": "AnalysisAgent",
            "content": (
                f"Detected **{len(raw_issues)}** issue(s) via GPT-4o vision analysis.\n\n"
                f"```json\n{json.dumps(raw_issues, indent=2)}\n```"
            ),
        })

        # ── Agent 2: CritiqueAgent ────────────────────────────────────────────
        critique_reply = _call_agent(
            self.client,
            system_prompt=_CRITIQUE_PROMPT,
            user_message=(
                f"Review and enrich this UI issue report.\n"
                f"Page: {url}\nViewport: {bp_label}\n\n"
                f"{json.dumps(raw_issues, indent=2)}"
            ),
        )
        critiqued = _extract_json(critique_reply) or raw_issues

        conversation_log.append({
            "agent": "CritiqueAgent",
            "content": critique_reply or "_No response._",
        })

        # ── Agent 3: SeverityAgent ────────────────────────────────────────────
        severity_reply = _call_agent(
            self.client,
            system_prompt=_SEVERITY_PROMPT,
            user_message=(
                f"Reclassify severity for these issues.\n"
                f"Viewport: {bp_label}\n\n"
                f"{json.dumps(critiqued, indent=2)}"
            ),
        )
        final_issues = _extract_json(severity_reply) or critiqued

        conversation_log.append({
            "agent": "SeverityAgent",
            "content": severity_reply or "_No response._",
        })

        for issue in final_issues:
            issue["breakpoint"] = bp_label

        return final_issues, conversation_log
