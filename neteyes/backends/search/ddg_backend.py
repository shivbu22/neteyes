"""DuckDuckGo Search backend (Zero-config, completely free)."""

from __future__ import annotations

import json
import re
import time
import warnings
from typing import Any, List, Optional, Tuple
from urllib.parse import unquote

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*duckduckgo_search.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*ddgs.*")

from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


class DuckDuckGoBackend(BaseBackend):
    id = "ddg_search"
    name = "DuckDuckGo Search Engine"
    priority = 10
    description = "Free, zero-config web search with instant answer and snippet extraction"
    backend_type = BackendType.HYBRID
    requires_auth = False
    dependencies = ["duckduckgo-search", "httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        if self.is_python_module_available("duckduckgo_search"):
            return HealthStatus.HEALTHY, "duckduckgo_search package installed and ready"
        return HealthStatus.HEALTHY, "Native DuckDuckGo Lite HTTP fallback is active (zero dependencies)"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        query = kwargs.get("query", "")
        if query:
            if self.is_binary_available("ddgs"):
                return f'ddgs text -k "{query}" -m 10'
            return f'curl -sL "https://html.duckduckgo.com/html/?q={query}"'
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

        # Try duckduckgo_search library first with warnings silenced
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=limit))

            if results:
                md_lines = [f"# Search Results: `{query}`\n"]
                data_items = []
                for idx, r in enumerate(results, 1):
                    title = r.get("title", "Untitled")
                    href = r.get("href", "")
                    body = r.get("body", "")
                    md_lines.append(f"### {idx}. [{title}]({href})")
                    md_lines.append(f"{body}\n")
                    data_items.append({
                        "title": title,
                        "url": href,
                        "snippet": body,
                    })

                return self._make_result(
                    True, "search", action, start_time,
                    data=data_items,
                    markdown="\n".join(md_lines),
                    raw=json.dumps(data_items, indent=2),
                    metadata={"query": query, "count": len(data_items), "engine": "ddgs"}
                )
        except Exception:
            # Fall back to direct HTML lite scrape
            pass

        # Native HTTP fallback
        try:
            client = get_http_client(
                platform="search",
                timeout=15.0,
                extra_headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    "Referer": "https://html.duckduckgo.com/",
                }
            )
            resp = client.post("https://html.duckduckgo.com/html/", data={"q": query})
            resp.raise_for_status()
            html = resp.text

            # Parse results from DDG HTML
            # Results are in <a class="result__url" href="..."> and <a class="result__snippet" ...>
            matches = re.findall(
                r'<h2 class="result__title">.*?<a class="result__url" href="([^"]+)">(.*?)</a>.*?</h2>.*?<a class="result__snippet"[^>]*>(.*?)</a>',
                html,
                re.DOTALL | re.IGNORECASE
            )

            # Secondary regex pattern for alternate html markup
            if not matches:
                matches = re.findall(
                    r'<a class="result__snippet"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                    html,
                    re.DOTALL | re.IGNORECASE
                )

            data_items = []
            md_lines = [f"# Search Results: `{query}` (Fallback Engine)\n"]

            # If regex didn't catch structured table, do a robust general extraction
            link_pattern = re.findall(r'<a\s+class="result__url"\s+href="([^"]+)">', html)
            snippet_pattern = re.findall(r'<a\s+class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)

            for idx, raw_link in enumerate(link_pattern[:limit], 1):
                clean_url = raw_link
                if "uddg=" in raw_link:
                    m = re.search(r"uddg=([^&]+)", raw_link)
                    if m:
                        clean_url = unquote(m.group(1))

                snippet = ""
                if idx - 1 < len(snippet_pattern):
                    snippet = re.sub(r"<[^>]+>", "", snippet_pattern[idx - 1]).strip()

                md_lines.append(f"### {idx}. [{clean_url}]({clean_url})")
                if snippet:
                    md_lines.append(f"{snippet}\n")

                data_items.append({
                    "title": clean_url,
                    "url": clean_url,
                    "snippet": snippet,
                })

            if not data_items:
                return self._make_result(
                    False, "search", action, start_time,
                    error=f"No results found for query '{query}' or rate limited by search provider."
                )

            return self._make_result(
                True, "search", action, start_time,
                data=data_items,
                markdown="\n".join(md_lines),
                raw=json.dumps(data_items, indent=2),
                metadata={"query": query, "count": len(data_items), "engine": "ddg_html"}
            )

        except Exception as e:
            return self._make_result(
                False, "search", action, start_time,
                error=f"DuckDuckGo search error: {str(e)}"
            )
