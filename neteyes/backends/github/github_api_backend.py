"""GitHub REST API backend."""

from __future__ import annotations

import base64
import json
import os
import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


class GitHubApiBackend(BaseBackend):
    id = "github_api"
    name = "GitHub REST API"
    priority = 20
    description = "Direct REST API client with optional GITHUB_TOKEN support for repos, issues, and readmes"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        auth_note = " (authenticated with token)" if token else " (unauthenticated, 60 req/hr rate limit)"
        return HealthStatus.HEALTHY, f"GitHub REST API available{auth_note}"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        repo = kwargs.get("repo", "")
        if action in ("repo", "view") and repo:
            return f'curl -sL -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/{repo}"'
        elif action == "readme" and repo:
            return f'curl -sL -H "Accept: application/vnd.github.v3.raw" "https://api.github.com/repos/{repo}/readme"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "NetEyes/0.1.0",
        }
        if token:
            headers["Authorization"] = f"token {token}"

        client = get_http_client(platform="github", timeout=15.0, extra_headers=headers)
        repo = kwargs.get("repo", "")

        try:
            if action in ("repo", "view"):
                if not repo:
                    return self._make_result(
                        False, "github", action, start_time,
                        error="Missing required argument 'repo'"
                    )
                resp = client.get(f"https://api.github.com/repos/{repo}")
                resp.raise_for_status()
                data = resp.json()

                full_name = data.get("full_name", repo)
                desc = data.get("description", "")
                stars = data.get("stargazers_count", 0)
                forks = data.get("forks_count", 0)
                language = data.get("language", "Unknown")
                html_url = data.get("html_url", f"https://github.com/{repo}")

                markdown_output = (
                    f"# GitHub Repo: [{full_name}]({html_url})\n\n"
                    f"**Language:** {language} | **Stars:** {stars:,} | **Forks:** {forks:,}\n\n"
                    f"**Description:**\n{desc}\n"
                )
                return self._make_result(
                    True, "github", action, start_time,
                    data=data,
                    markdown=markdown_output,
                    raw=json.dumps(data, indent=2),
                    metadata={"repo": repo}
                )

            elif action == "readme":
                if not repo:
                    return self._make_result(
                        False, "github", action, start_time,
                        error="Missing required argument 'repo'"
                    )
                resp = client.get(f"https://api.github.com/repos/{repo}/readme")
                resp.raise_for_status()
                data = resp.json()
                content_b64 = data.get("content", "")
                readme_text = base64.b64decode(content_b64).decode("utf-8", errors="replace")

                return self._make_result(
                    True, "github", action, start_time,
                    data={"repo": repo, "readme": readme_text},
                    markdown=readme_text,
                    raw=readme_text,
                    metadata={"repo": repo}
                )

            elif action in ("issues", "issue_list"):
                if not repo:
                    return self._make_result(
                        False, "github", action, start_time,
                        error="Missing required argument 'repo'"
                    )
                limit = int(kwargs.get("limit", 10))
                resp = client.get(f"https://api.github.com/repos/{repo}/issues?per_page={limit}&state=open")
                resp.raise_for_status()
                items = resp.json()

                md_lines = [f"# Open Issues for {repo}\n"]
                for it in items:
                    # Skip PRs which GitHub issues API includes
                    if "pull_request" in it:
                        continue
                    num = it.get("number")
                    title = it.get("title")
                    user = it.get("user", {}).get("login", "unknown")
                    url = it.get("html_url")
                    md_lines.append(f"- [#{num} {title}]({url}) by @{user}")

                return self._make_result(
                    True, "github", action, start_time,
                    data=items,
                    markdown="\n".join(md_lines),
                    raw=json.dumps(items, indent=2),
                    metadata={"repo": repo}
                )

            return self._make_result(
                False, "github", action, start_time,
                error=f"Unsupported action '{action}' for GitHub REST API."
            )

        except Exception as e:
            return self._make_result(
                False, "github", action, start_time,
                error=f"GitHub API request failed: {str(e)}"
            )
