"""Trafilatura backend for Web page extraction."""

from __future__ import annotations

import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


class TrafilaturaBackend(BaseBackend):
    id = "trafilatura"
    name = "Trafilatura (Local Readability)"
    priority = 10
    description = "High-precision local HTML-to-text/markdown parser with noise and boilerplate removal"
    backend_type = BackendType.PYTHON_MODULE
    requires_auth = False
    dependencies = ["trafilatura"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        if self.is_python_module_available("trafilatura"):
            return HealthStatus.HEALTHY, "trafilatura Python package is installed and operational"
        return HealthStatus.MISSING_DEPENDENCY, "trafilatura is not installed. Run: pip install trafilatura"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        url = kwargs.get("url", "")
        if action == "extract" and url:
            if self.is_binary_available("trafilatura"):
                return f'trafilatura -u "{url}" --output-format markdown'
            return f'python -m trafilatura -u "{url}" --output-format markdown'
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
            import trafilatura
            # Fetch content
            client = get_http_client(platform="web")
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text

            # Extract structured text and metadata
            extracted_text = trafilatura.extract(
                html,
                url=url,
                output_format="markdown",
                include_comments=False,
                include_tables=True,
                include_links=True,
            )
            metadata = trafilatura.extract_metadata(html, default_url=url)

            title = metadata.title if metadata and metadata.title else "Untitled Page"
            author = metadata.author if metadata and metadata.author else "Unknown"
            date = metadata.date if metadata and metadata.date else "Unknown"

            content = extracted_text or "No readable main content extracted."
            markdown_output = f"# {title}\n\n"
            markdown_output += f"**Source:** {url}  \n"
            markdown_output += f"**Author:** {author} | **Date:** {date}\n\n---\n\n"
            markdown_output += content

            data = {
                "title": title,
                "author": author,
                "date": date,
                "url": url,
                "content": content,
            }
            return self._make_result(
                True, "web", action, start_time,
                data=data,
                markdown=markdown_output,
                raw=content,
                metadata={"status_code": resp.status_code, "extractor": "trafilatura"}
            )
        except Exception as e:
            return self._make_result(
                False, "web", action, start_time,
                error=f"Trafilatura extraction failed: {str(e)}"
            )
