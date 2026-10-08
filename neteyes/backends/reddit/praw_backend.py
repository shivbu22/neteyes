"""PRAW (Python Reddit API Wrapper) backend for authenticated Reddit actions."""

from __future__ import annotations

import os
import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus


class PrawBackend(BaseBackend):
    id = "praw"
    name = "PRAW (Official API Wrapper)"
    priority = 20
    description = "Authenticated Reddit API access via client_id/client_secret credentials"
    backend_type = BackendType.PYTHON_MODULE
    requires_auth = True
    dependencies = ["praw"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        if not self.is_python_module_available("praw"):
            return HealthStatus.MISSING_DEPENDENCY, "praw not installed. Run: pip install praw"
        if not os.environ.get("REDDIT_CLIENT_ID") or not os.environ.get("REDDIT_CLIENT_SECRET"):
            return HealthStatus.REQUIRES_AUTH, "Missing REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET environment variables"
        return HealthStatus.HEALTHY, "PRAW configured with valid environment credentials"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        try:
            import praw
        except ImportError:
            return self._make_result(
                False, "reddit", action, start_time,
                error="praw library is not installed."
            )

        client_id = os.environ.get("REDDIT_CLIENT_ID")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        user_agent = os.environ.get("REDDIT_USER_AGENT", "NetEyes/0.1.0")

        if not client_id or not client_secret:
            return self._make_result(
                False, "reddit", action, start_time,
                error="REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables are required for PRAW."
            )

        try:
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )

            if action in ("subreddit", "sub"):
                sub_name = kwargs.get("subreddit", "python")
                limit = int(kwargs.get("limit", 10))
                sub = reddit.subreddit(sub_name)
                posts = []
                md_lines = [f"# Reddit r/{sub_name} (via PRAW)\n"]
                for p in sub.hot(limit=limit):
                    md_lines.append(f"- **[{p.title}]({p.url})** (Score: {p.score:,}, Comments: {p.num_comments:,})")
                    posts.append({
                        "id": p.id,
                        "title": p.title,
                        "score": p.score,
                        "url": p.url,
                    })
                return self._make_result(
                    True, "reddit", action, start_time,
                    data=posts,
                    markdown="\n".join(md_lines),
                )
            return self._make_result(
                False, "reddit", action, start_time,
                error=f"Unsupported action '{action}' for PRAW backend."
            )
        except Exception as e:
            return self._make_result(
                False, "reddit", action, start_time,
                error=f"PRAW execution error: {str(e)}"
            )
