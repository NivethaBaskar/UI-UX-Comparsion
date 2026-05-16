import os
import requests
from datetime import datetime, timezone

SEVERITY_TO_PRIORITY = {
    "critical": "Highest",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class JiraClient:
    def __init__(self, domain: str, email: str, api_token: str, project_key: str):
        # Strip any protocol prefix the user may have included
        domain = domain.strip().rstrip("/")
        for prefix in ("https://", "http://"):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        self.domain = domain
        self.base_url = f"https://{self.domain}/rest/api/3"
        self.auth = (email, api_token)
        self.project_key = project_key
        self.json_headers = {"Accept": "application/json", "Content-Type": "application/json"}

    def _adf_text(self, text: str) -> dict:
        return {"type": "paragraph", "content": [{"type": "text", "text": str(text)}]}

    def _adf_heading(self, text: str, level: int = 2) -> dict:
        return {"type": "heading", "attrs": {"level": level}, "content": [{"type": "text", "text": text}]}

    def _adf_bullet(self, items: list[str]) -> dict:
        return {
            "type": "bulletList",
            "content": [
                {"type": "listItem", "content": [self._adf_text(item)]}
                for item in items
            ],
        }

    def _build_description(self, issue: dict, url: str, timestamp: str) -> dict:
        return {
            "type": "doc",
            "version": 1,
            "content": [
                self._adf_heading("Issue Summary"),
                self._adf_text(issue.get("issue", "No description provided.")),
                self._adf_heading("Affected Component"),
                self._adf_text(issue.get("component", "Unknown")),
                self._adf_heading("Probable Root Cause"),
                self._adf_text(issue.get("root_cause", "Requires manual investigation.")),
                self._adf_heading("Suggested Fix"),
                self._adf_text(issue.get("suggested_fix", "Review implementation against Figma spec.")),
                self._adf_heading("Environment Details"),
                self._adf_bullet([
                    f"URL Tested: {url}",
                    f"Detected At: {timestamp}",
                    f"Severity: {issue.get('severity', 'medium').upper()}",
                    f"AI Confidence: {issue.get('confidence', 'N/A')}%",
                    f"Responsible Team: {issue.get('team', 'Frontend')}",
                    f"Issue Type: {issue.get('type', 'ui')}",
                ]),
            ],
        }

    def create_ticket(self, issue: dict, url: str, timestamp: str) -> dict:
        # Use only the required fields — priority/labels/issuetype names vary per project
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": issue.get("jira_title", f"[UI] {issue.get('issue', 'Visual regression detected')}"),
                "description": self._build_description(issue, url, timestamp),
                "issuetype": {"name": "Task"},
            }
        }

        response = requests.post(
            f"{self.base_url}/issue",
            json=payload,
            auth=self.auth,
            headers=self.json_headers,
            timeout=15,
        )

        if not response.ok:
            try:
                detail = response.json()
                msgs = detail.get("errorMessages", [])
                errs = detail.get("errors", {})
                raise requests.HTTPError(
                    f"Jira {response.status_code}: {msgs or errs}",
                    response=response,
                )
            except (ValueError, KeyError):
                response.raise_for_status()

        return response.json()

    def attach_file(self, issue_key: str, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        try:
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                response = requests.post(
                    f"{self.base_url}/issue/{issue_key}/attachments",
                    auth=self.auth,
                    headers={"X-Atlassian-Token": "no-check"},
                    files={"file": (filename, f, "image/png")},
                    timeout=30,
                )
            response.raise_for_status()
            return True
        except Exception:
            return False

    def create_tickets_for_issues(
        self,
        issues: list,
        url: str,
        figma_path: str,
        ui_path: str,
        diff_path: str,
        severity_threshold: str = "low",
    ) -> list:
        """Create Jira tickets for all issues at or above the severity threshold."""
        threshold_level = SEVERITY_ORDER.get(severity_threshold.lower(), 3)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        results = []

        for issue in issues:
            sev = issue.get("severity", "low").lower()
            if SEVERITY_ORDER.get(sev, 3) > threshold_level:
                results.append({"issue": issue, "status": "skipped", "reason": f"severity '{sev}' is below threshold '{severity_threshold}'"})
                continue
            try:
                ticket = self.create_ticket(issue, url, timestamp)
                key = ticket.get("key", "")
                for path in [figma_path, ui_path, diff_path]:
                    self.attach_file(key, path)
                results.append({
                    "issue": issue,
                    "status": "created",
                    "ticket_key": key,
                    "ticket_url": f"https://{self.domain}/browse/{key}",
                })
            except Exception as e:
                results.append({"issue": issue, "status": "failed", "error": str(e)})

        return results
