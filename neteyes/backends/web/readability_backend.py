"""Direct Readability & Markdown backend for Web page extraction."""

from __future__ import annotations

import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client, simple_html_to_markdown


class DirectReadabilityBackend(BaseBackend):
    id = "direct_http"
    name = "Direct HTTP & Native Markdown"
    priority = 30
    description = "Direct HTTP fetch with native HTML-to-Markdown cleaner (zero external dependencies)"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        return HealthStatus.HEALTHY, "Native HTTP & Markdown engine is operational"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        url = kwargs.get("url", "")
        if action == "extract" and url:
            return f'curl -sL "{url}"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        url = kwargs.get("url")
        if not url:
            return self._make_result(
                False, "web", action, start_time,
                error="Missing required argument 'url'"
            )

        try:
            client = get_http_client(platform="web", timeout=20.0)
            resp = client.get(url)
            resp.raise_for_status()

            # Attempt to use BeautifulSoup if available, else regex cleaner
            html_text = resp.text
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_text, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else "Web Page"
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    tag.decompose()
                body = soup.find("main") or soup.find("article") or soup.body or soup
                cleaned_markdown = simple_html_to_markdown(str(body))
            except Exception:
                title = "Web Page"
                cleaned_markdown = simple_html_to_markdown(html_text)

            markdown_output = f"# {title}\n\n**Source:** {url}\n\n---\n\n{cleaned_markdown}"
            data = {
                "title": title,
                "url": url,
                "content": cleaned_markdown,
            }
            return self._make_result(
                True, "web", action, start_time,
                data=data,
                markdown=markdown_output,
                raw=html_text,
                metadata={"status_code": resp.status_code, "extractor": "direct_http"}
            )
        except Exception as e:
            return self._make_result(
                False, "web", action, start_time,
                error=f"Direct HTTP fetch failed: {str(e)}"
            )
