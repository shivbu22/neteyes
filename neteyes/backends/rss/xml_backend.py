"""Zero-dependency ElementTree RSS/Atom fallback backend."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client, simple_html_to_markdown


class XmlRssBackend(BaseBackend):
    id = "xml_rss"
    name = "Native XML Feed Parser"
    priority = 20
    description = "Standard library XML parser for RSS and Atom feeds (zero dependencies)"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = []

    def check_health(self) -> Tuple[HealthStatus, str]:
        return HealthStatus.HEALTHY, "Standard Python xml.etree engine is available"

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

            root = ET.fromstring(resp.content)
            items = []

            # Check if RSS 2.0 (<rss><channel><item>)
            channel = root.find("channel")
            if channel is not None:
                feed_title = channel.findtext("title", "RSS Feed")
                limit = int(kwargs.get("limit", 10))
                for item in channel.findall("item")[:limit]:
                    items.append({
                        "title": item.findtext("title", "Untitled"),
                        "link": item.findtext("link", ""),
                        "published": item.findtext("pubDate", ""),
                        "summary": simple_html_to_markdown(item.findtext("description", "")),
                    })
            else:
                # Atom feed
                feed_title = root.findtext("{http://www.w3.org/2005/Atom}title", "Atom Feed")
                limit = int(kwargs.get("limit", 10))
                for entry in root.findall("{http://www.w3.org/2005/Atom}entry")[:limit]:
                    link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
                    link = link_elem.get("href", "") if link_elem is not None else ""
                    items.append({
                        "title": entry.findtext("{http://www.w3.org/2005/Atom}title", "Untitled"),
                        "link": link,
                        "published": entry.findtext("{http://www.w3.org/2005/Atom}updated", ""),
                        "summary": simple_html_to_markdown(entry.findtext("{http://www.w3.org/2005/Atom}summary", "")),
                    })

            md_lines = [f"# Feed: {feed_title}\n"]
            for idx, item in enumerate(items, 1):
                md_lines.append(f"### {idx}. [{item['title']}]({item['link']})")
                md_lines.append(f"Published: {item['published']}\n")
                if item["summary"]:
                    md_lines.append(f"> {item['summary'][:300]}...\n")

            return self._make_result(
                True, "rss", action, start_time,
                data=items,
                markdown="\n".join(md_lines),
                metadata={"url": url, "count": len(items)}
            )

        except Exception as e:
            return self._make_result(
                False, "rss", action, start_time,
                error=f"Native XML parse failed: {str(e)}"
            )
