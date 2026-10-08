"""Jina Reader backend for Web page extraction."""

from __future__ import annotations

import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


class JinaReaderBackend(BaseBackend):
    id = "jina_reader"
    name = "Jina Reader (r.jina.ai)"
    priority = 20
    description = "Cloud web reader supporting client-side JavaScript rendering and returning clean Markdown"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        # Quick non-destructive network check to r.jina.ai
        try:
            client = get_http_client(timeout=5.0)
            resp = client.get("https://r.jina.ai/https://example.com")
            if resp.status_code == 200:
                return HealthStatus.HEALTHY, "r.jina.ai is reachable and responsive"
            return HealthStatus.DEGRADED, f"r.jina.ai returned status {resp.status_code}"
        except Exception as e:
            return HealthStatus.UNAVAILABLE, f"r.jina.ai connection error: {str(e)}"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        url = kwargs.get("url", "")
        if action == "extract" and url:
            return f'curl -sL "https://r.jina.ai/{url}"'
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
            client = get_http_client(timeout=30.0)
            jina_endpoint = f"https://r.jina.ai/{url}"
            resp = client.get(
                jina_endpoint,
                headers={
                    "X-Return-Format": "markdown",
                    "Accept": "text/markdown",
                }
            )
            resp.raise_for_status()
            markdown_content = resp.text.strip()

            data = {
                "url": url,
                "content": markdown_content,
                "extractor": "jina_reader"
            }
            return self._make_result(
                True, "web", action, start_time,
                data=data,
                markdown=markdown_content,
                raw=markdown_content,
                metadata={"status_code": resp.status_code, "extractor": "jina_reader"}
            )
        except Exception as e:
            return self._make_result(
                False, "web", action, start_time,
                error=f"Jina Reader extraction failed: {str(e)}"
            )
