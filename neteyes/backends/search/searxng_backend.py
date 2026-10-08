"""SearXNG meta-search engine backend."""

from __future__ import annotations

import json
import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


class SearxngBackend(BaseBackend):
    id = "searxng"
    name = "SearXNG Meta-Search"
    priority = 20
    description = "Privacy-respecting open meta-search engine aggregating Google, Bing, Wikipedia"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    DEFAULT_INSTANCE = "https://searx.be"

    def check_health(self) -> Tuple[HealthStatus, str]:
        try:
            client = get_http_client(platform="search", timeout=5.0)
            resp = client.get(f"{self.DEFAULT_INSTANCE}/search?q=test&format=json")
            if resp.status_code == 200:
                return HealthStatus.HEALTHY, f"SearXNG instance ({self.DEFAULT_INSTANCE}) is online"
            return HealthStatus.DEGRADED, f"SearXNG returned status {resp.status_code}"
        except Exception:
            return HealthStatus.DEGRADED, "Public SearXNG instance latency high, secondary fallback ready"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        query = kwargs.get("query", "")
        if query:
            return f'curl -sL "{self.DEFAULT_INSTANCE}/search?q={query}&format=json"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        query = kwargs.get("query")
        if not query:
            return self._make_result(
                False, "search", action, start_time,
                error="Missing required argument 'query'"
            )

        limit = int(kwargs.get("limit", 10))
        client = get_http_client(platform="search", timeout=15.0)

        # Try default and backup instances
        instances = [self.DEFAULT_INSTANCE, "https://search.ononoki.org", "https://searx.space"]
        last_error = ""

        for inst in instances:
            try:
                endpoint = f"{inst}/search?q={query}&format=json"
                resp = client.get(endpoint)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])[:limit]
                    if results:
                        md_lines = [f"# SearXNG Results: `{query}` ({inst})\n"]
                        data_items = []
                        for idx, r in enumerate(results, 1):
                            title = r.get("title", "Untitled")
                            url = r.get("url", "")
                            content = r.get("content", "")
                            md_lines.append(f"### {idx}. [{title}]({url})")
                            md_lines.append(f"{content}\n")
                            data_items.append({
                                "title": title,
                                "url": url,
                                "snippet": content,
                            })

                        return self._make_result(
                            True, "search", action, start_time,
                            data=data_items,
                            markdown="\n".join(md_lines),
                            raw=json.dumps(data_items, indent=2),
                            metadata={"instance": inst, "count": len(data_items)}
                        )
            except Exception as e:
                last_error = str(e)
                continue

        return self._make_result(
            False, "search", action, start_time,
            error=f"All SearXNG instances failed or timed out: {last_error}"
        )
