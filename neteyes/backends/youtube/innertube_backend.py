"""Lightweight direct endpoint backend for YouTube video metadata."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


class YouTubeDirectBackend(BaseBackend):
    id = "youtube_direct"
    name = "YouTube Direct Endpoint (oEmbed & Scrape)"
    priority = 30
    description = "Zero-dependency YouTube metadata extraction via public oEmbed and watch page scraping"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        return HealthStatus.HEALTHY, "YouTube public oEmbed client is operational"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        target = kwargs.get("url") or kwargs.get("video_id") or ""
        if target:
            clean_url = target if target.startswith("http") else f"https://www.youtube.com/watch?v={target}"
            return f'curl -sL "https://www.youtube.com/oembed?url={clean_url}&format=json"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        target = kwargs.get("url") or kwargs.get("video_id")
        if not target:
            return self._make_result(
                False, "youtube", action, start_time,
                error="Missing required argument 'url' or 'video_id'"
            )

        video_url = target if target.startswith("http") else f"https://www.youtube.com/watch?v={target}"

        try:
            client = get_http_client(platform="youtube", timeout=15.0)
            oembed_url = f"https://www.youtube.com/oembed?url={video_url}&format=json"
            resp = client.get(oembed_url)
            resp.raise_for_status()
            data = resp.json()

            title = data.get("title", "Untitled Video")
            author = data.get("author_name", "Unknown Channel")
            author_url = data.get("author_url", "")
            thumbnail = data.get("thumbnail_url", "")

            markdown_output = (
                f"# {title}\n\n"
                f"**Channel:** [{author}]({author_url})\n"
                f"**Video URL:** {video_url}\n"
                f"![Thumbnail]({thumbnail})\n"
            )

            return self._make_result(
                True, "youtube", action, start_time,
                data=data,
                markdown=markdown_output,
                raw=json.dumps(data, indent=2),
                metadata={"video_url": video_url}
            )
        except Exception as e:
            return self._make_result(
                False, "youtube", action, start_time,
                error=f"Direct YouTube fetch failed: {str(e)}"
            )
