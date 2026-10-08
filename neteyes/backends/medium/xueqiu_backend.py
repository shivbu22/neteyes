"""Xueqiu (雪球) financial market and community backend."""

from __future__ import annotations

import json
import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client, simple_html_to_markdown


class XueqiuBackend(BaseBackend):
    id = "xueqiu"
    name = "Xueqiu Financial API"
    priority = 10
    description = "Financial posts, stock quotes, and discussions from Xueqiu"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        return HealthStatus.HEALTHY, "Xueqiu client initialized"

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        client = get_http_client(
            platform="xueqiu",
            timeout=15.0,
            extra_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Referer": "https://xueqiu.com/",
            }
        )

        try:
            # First hit home page to acquire visitor cookie if not present
            client.get("https://xueqiu.com/")

            symbol = kwargs.get("symbol") or kwargs.get("stock")
            if action in ("quote", "stock") and symbol:
                endpoint = f"https://stock.xueqiu.com/v5/stock/quote.json?symbol={symbol}&extend=detail"
                resp = client.get(endpoint)
                resp.raise_for_status()
                data = resp.json()

                quote = data.get("data", {}).get("quote", {})
                name = quote.get("name", symbol)
                current = quote.get("current", 0)
                chg = quote.get("percent", 0)

                md = (
                    f"# 雪球: {name} ({symbol})\n\n"
                    f"**当前价:** {current} | **涨跌幅:** {chg}%\n"
                )
                return self._make_result(
                    True, "xueqiu", action, start_time,
                    data=data,
                    markdown=md,
                )

            query = kwargs.get("query")
            if action == "search" and query:
                endpoint = f"https://xueqiu.com/query/v1/search/status.json?q={query}&count=10"
                resp = client.get(endpoint)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("list", [])

                md_lines = [f"# 雪球搜索: `{query}`\n"]
                for idx, item in enumerate(items, 1):
                    title = item.get("title") or item.get("text", "")[:60]
                    clean_text = simple_html_to_markdown(item.get("text", ""))
                    user = item.get("user", {}).get("screen_name", "unknown")
                    md_lines.append(f"{idx}. **{title}** by @{user}")
                    if clean_text:
                        md_lines.append(f"> {clean_text[:200]}...\n")

                return self._make_result(
                    True, "xueqiu", action, start_time,
                    data=items,
                    markdown="\n".join(md_lines),
                )

            return self._make_result(
                False, "xueqiu", action, start_time,
                error=f"Unsupported action '{action}' for Xueqiu. Supported: quote, search"
            )

        except Exception as e:
            return self._make_result(
                False, "xueqiu", action, start_time,
                error=f"Xueqiu request failed: {str(e)}"
            )
