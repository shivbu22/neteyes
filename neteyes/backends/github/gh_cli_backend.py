"""Official GitHub CLI (gh) backend."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus


class GhCliBackend(BaseBackend):
    id = "gh_cli"
    name = "GitHub CLI (gh)"
    priority = 10
    description = "Official GitHub CLI tool with built-in token auth, repos, issues, and PR management"
    backend_type = BackendType.CLI_BINARY
    requires_auth = False
    dependencies = ["gh"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        if not self.is_binary_available("gh"):
            return HealthStatus.MISSING_DEPENDENCY, "gh binary not found on PATH. Install GitHub CLI: https://cli.github.com"

        # Check authentication status
        try:
            res = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                return HealthStatus.HEALTHY, "gh CLI is installed and authenticated"
            return HealthStatus.DEGRADED, "gh CLI installed but not logged in. Run: gh auth login"
        except Exception as e:
            return HealthStatus.DEGRADED, f"gh check failed: {str(e)}"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        repo = kwargs.get("repo", "")
        if action in ("repo", "view") and repo:
            return f"gh repo view {repo}"
        elif action in ("issues", "issue_list") and repo:
            return f"gh issue list -R {repo} --limit 10"
        elif action in ("prs", "pr_list") and repo:
            return f"gh pr list -R {repo} --limit 10"
        elif action == "api" and kwargs.get("endpoint"):
            return f"gh api {kwargs.get('endpoint')}"
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        if not self.is_binary_available("gh"):
            return self._make_result(
                False, "github", action, start_time,
                error="gh executable binary is not installed or not in PATH."
            )

        repo = kwargs.get("repo", "")
        cmd = []

        if action in ("repo", "view"):
            if not repo:
                return self._make_result(
                    False, "github", action, start_time,
                    error="Missing required argument 'repo' (e.g. owner/repo)"
                )
            cmd = ["gh", "repo", "view", repo, "--json", "name,owner,description,stargazerCount,forkCount,url,defaultBranchRef"]

        elif action in ("issues", "issue_list"):
            if not repo:
                return self._make_result(
                    False, "github", action, start_time,
                    error="Missing required argument 'repo'"
                )
            limit = str(kwargs.get("limit", 10))
            cmd = ["gh", "issue", "list", "-R", repo, "--limit", limit, "--json", "number,title,author,state,createdAt,url"]

        elif action in ("prs", "pr_list"):
            if not repo:
                return self._make_result(
                    False, "github", action, start_time,
                    error="Missing required argument 'repo'"
                )
            limit = str(kwargs.get("limit", 10))
            cmd = ["gh", "pr", "list", "-R", repo, "--limit", limit, "--json", "number,title,author,state,createdAt,url"]

        else:
            return self._make_result(
                False, "github", action, start_time,
                error=f"Unsupported action '{action}' for gh CLI backend. Supported: repo, issues, prs"
            )

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode != 0:
                return self._make_result(
                    False, "github", action, start_time,
                    error=f"gh CLI failed: {proc.stderr.strip()}"
                )

            data = json.loads(proc.stdout)
            markdown_lines = []

            if action in ("repo", "view"):
                name = data.get("name")
                owner = data.get("owner", {}).get("login", "")
                desc = data.get("description", "")
                stars = data.get("stargazerCount", 0)
                forks = data.get("forkCount", 0)
                url = data.get("url", f"https://github.com/{owner}/{name}")

                markdown_lines = [
                    f"# GitHub Repository: [{owner}/{name}]({url})\n",
                    f"**Stars:** {stars:,} | **Forks:** {forks:,}\n",
                    f"**Description:** {desc}\n",
                ]

            elif action in ("issues", "issue_list"):
                markdown_lines.append(f"# Issues for {repo}\n")
                for item in data:
                    num = item.get("number")
                    title = item.get("title")
                    author = item.get("author", {}).get("login", "unknown")
                    url = item.get("url")
                    markdown_lines.append(f"- [#{num} {title}]({url}) by @{author}")

            elif action in ("prs", "pr_list"):
                markdown_lines.append(f"# Pull Requests for {repo}\n")
                for item in data:
                    num = item.get("number")
                    title = item.get("title")
                    author = item.get("author", {}).get("login", "unknown")
                    url = item.get("url")
                    markdown_lines.append(f"- [#{num} {title}]({url}) by @{author}")

            return self._make_result(
                True, "github", action, start_time,
                data=data,
                markdown="\n".join(markdown_lines),
                raw=proc.stdout,
                metadata={"repo": repo}
            )

        except Exception as e:
            return self._make_result(
                False, "github", action, start_time,
                error=f"gh CLI execution error: {str(e)}"
            )
