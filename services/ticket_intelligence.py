import os
import json
from openai import OpenAI

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_FALLBACK_TEAMS = {
    "navbar": "Frontend Platform", "header": "Frontend Platform", "footer": "Frontend Platform",
    "checkout": "Checkout Team", "cart": "Checkout Team", "payment": "Checkout Team",
    "button": "Design System", "modal": "Design System", "input": "Design System",
    "hero": "Marketing", "banner": "Marketing", "carousel": "Marketing",
    "form": "Auth Team", "login": "Auth Team", "signup": "Auth Team",
}


def _fallback_team(component: str) -> str:
    lower = component.lower()
    for key, team in _FALLBACK_TEAMS.items():
        if key in lower:
            return team
    return "Frontend"


def _apply_fallback_fields(issues: list) -> list:
    for issue in issues:
        sev = issue.get("severity", "medium").lower()
        comp = issue.get("component", "Unknown")
        issue.setdefault("root_cause", "Unknown — manual inspection required")
        issue.setdefault("suggested_fix", "Review component implementation against Figma spec")
        issue.setdefault("team", _fallback_team(comp))
        issue.setdefault("confidence", 70)
        issue.setdefault(
            "jira_title",
            f"[{sev.upper()}] {issue.get('issue', 'UI Issue')} in {comp}"
        )
    return issues


def enrich_issues(issues: list, url: str) -> list:
    """Use GPT-4o to group, deduplicate, add root cause, and suggest team ownership."""
    if not issues:
        return issues

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return sorted(_apply_fallback_fields(issues), key=lambda x: SEVERITY_ORDER.get(x.get("severity", "low").lower(), 3))

    client = OpenAI(api_key=api_key)

    prompt = f"""You are a senior frontend QA engineer reviewing UI regression issues detected on: {url}

Issues detected:
{json.dumps(issues, indent=2)}

Tasks:
1. Remove exact duplicates or near-identical issues — keep the most descriptive one.
2. Normalize severity to exactly one of: "critical", "high", "medium", "low".
3. For each remaining issue add these fields:
   - "root_cause": Most probable technical cause (e.g. CSS specificity conflict, missing responsive breakpoint, wrong design token, asset loading failure).
   - "suggested_fix": One concise, actionable fix a developer can act on immediately.
   - "team": Likely responsible team based on the component name (e.g. "Design System", "Frontend Platform", "Checkout Team", "Marketing", "Auth Team").
   - "confidence": Integer 0-100 representing your confidence this is a genuine visual regression.
   - "jira_title": Jira ticket title in format "[SEVERITY] <short description>" e.g. "[HIGH] Navbar top padding 12px off on desktop".

Return ONLY a valid JSON array. No markdown fences, no extra text.
Every object must include: type, component, issue, severity, root_cause, suggested_fix, team, confidence, jira_title."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            parts = content.split("```")
            content = parts[1][4:] if parts[1].startswith("json") else parts[1]

        enriched = json.loads(content)
        # Re-attach bbox from original issues by matching component name (LLM may drop it)
        bbox_map = {i.get("component", ""): i.get("bbox") for i in issues if i.get("bbox")}
        for item in enriched:
            if not item.get("bbox"):
                item["bbox"] = bbox_map.get(item.get("component", ""))
        return sorted(enriched, key=lambda x: SEVERITY_ORDER.get(x.get("severity", "low").lower(), 3))

    except Exception:
        return sorted(_apply_fallback_fields(issues), key=lambda x: SEVERITY_ORDER.get(x.get("severity", "low").lower(), 3))
