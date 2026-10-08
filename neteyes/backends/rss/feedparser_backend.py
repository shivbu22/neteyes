"""Feedparser backend for RSS and Atom feeds."""

from __future__ import annotations

import json
import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client, simple_html_to_markdown


class FeedparserBackend(BaseBackend):
    id = "feedparser"
    name = "Feedparser (RSS & Atom)"
    priority = 10
    description = "Universal RSS 2.0 and Atom XML feed parser with enclosure and metadata support"
    backend_type = BackendType.PYTHON_MODULE
    requires_auth = False
    dependencies = ["feedparser"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        if self.is_python_module_available("feedparser"):
            return HealthStatus.HEALTHY, "feedparser library is installed and operational"
        return HealthStatus.MISSING_DEPENDENCY, "feedparser not installed. Run: pip install feedparser"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        url = kwargs.get("url", "")
        if url:
            return f'curl -sL "{url}"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        url = kwargs.get("url")
        if not url:
            return self._make_result(
                False, "rss", action, start_time,
                error="Missing required argument 'url'"
            )

        try:
            import feedparser
            client = get_http_client(
                platform="rss",
                timeout=20.0,
                extra_headers={
                    "User-Agent": "curl/8.0.1 (FeedReader/1.0)",
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
                }
            )
            resp = client.get(url)
            resp.raise_for_status()

            feed = feedparser.parse(resp.text)
            feed_title = feed.feed.get("title", "RSS Feed")
            feed_link = feed.feed.get("link", url)
            feed_desc = feed.feed.get("description", "")

            limit = int(kwargs.get("limit", 10))
            entries = feed.entries[:limit]

            md_lines = [
                f"# RSS Feed: [{feed_title}]({feed_link})\n",
                f"**Description:** {feed_desc}\n",
                f"**Total Items:** {len(entries)}\n",
                "---\n"
            ]

            parsed_entries = []
            for idx, entry in enumerate(entries, 1):
                item_title = entry.get("title", "Untitled")
                item_link = entry.get("link", "")
                item_published = entry.get("published", entry.get("updated", "Unknown date"))
                raw_summary = entry.get("summary", "")
                clean_summary = simple_html_to_markdown(raw_summary)

                md_lines.append(f"### {idx}. [{item_title}]({item_link})")
                md_lines.append(f"**Published:** {item_published}\n")
                if clean_summary:
                    md_lines.append(f"> {clean_summary[:400] + ('...' if len(clean_summary) > 400 else '')}\n")

                parsed_entries.append({
                    "title": item_title,
                    "link": item_link,
                    "published": item_published,
                    "summary": clean_summary,
                })

            data = {
                "title": feed_title,
                "link": feed_link,
                "description": feed_desc,
                "entries": parsed_entries,
            }
            return self._make_result(
                True, "rss", action, start_time,
                data=data,
                markdown="\n".join(md_lines),
                raw=json.dumps(data, indent=2),
                metadata={"url": url, "count": len(parsed_entries)}
            )

        except Exception as e:
            return self._make_result(
                False, "rss", action, start_time,
                error=f"Feed parsing failed: {str(e)}"
            )
