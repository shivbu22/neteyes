"""yt-dlp backend for YouTube video metadata, search, and subtitles."""

from __future__ import annotations

import json
import time
from typing import Any, List, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus


class YtDlpBackend(BaseBackend):
    id = "yt_dlp"
    name = "yt-dlp (Rich Metadata & Search)"
    priority = 20
    description = "Comprehensive video metadata extraction, playlist support, and YouTube search"
    backend_type = BackendType.HYBRID
    requires_auth = False
    dependencies = ["yt-dlp"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        if self.is_python_module_available("yt_dlp") or self.is_binary_available("yt-dlp"):
            return HealthStatus.HEALTHY, "yt-dlp is available (python library or CLI binary)"
        return HealthStatus.MISSING_DEPENDENCY, "yt-dlp not found. Run: pip install yt-dlp"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        target = kwargs.get("url") or kwargs.get("video_id") or ""
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 5)

        if action == "search" and query:
            return f'yt-dlp --dump-json "ytsearch{limit}:{query}"'
        elif action in ("info", "metadata", "extract") and target:
            return f'yt-dlp --dump-json --skip-download "{target}"'
        elif action in ("transcript", "subtitles") and target:
            return f'yt-dlp --write-auto-sub --skip-download --sub-lang en "{target}"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        try:
            import yt_dlp
        except ImportError:
            return self._make_result(
                False, "youtube", action, start_time,
                error="yt-dlp Python package is not installed."
            )

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist" if action == "search" else False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if action == "search":
                    query = kwargs.get("query")
                    if not query:
                        return self._make_result(
                            False, "youtube", action, start_time,
                            error="Missing required argument 'query'"
                        )
                    limit = int(kwargs.get("limit", 5))
                    search_term = f"ytsearch{limit}:{query}"
                    info = ydl.extract_info(search_term, download=False)
                    entries = info.get("entries", []) if info else []

                    markdown_lines = [f"# YouTube Search: `{query}`\n"]
                    data_items = []
                    for idx, item in enumerate(entries, 1):
                        title = item.get("title", "Untitled")
                        url = item.get("url") or f"https://www.youtube.com/watch?v={item.get('id', '')}"
                        uploader = item.get("uploader", "Unknown channel")
                        duration = item.get("duration", "N/A")
                        markdown_lines.append(f"{idx}. **[{title}]({url})**")
                        markdown_lines.append(f"   *Channel:* {uploader} | *Duration:* {duration}s\n")
                        data_items.append({
                            "title": title,
                            "url": url,
                            "channel": uploader,
                            "id": item.get("id"),
                        })

                    return self._make_result(
                        True, "youtube", action, start_time,
                        data=data_items,
                        markdown="\n".join(markdown_lines),
                        raw=json.dumps(data_items, indent=2),
                        metadata={"result_count": len(data_items)}
                    )

                else:
                    # Video info/metadata
                    target = kwargs.get("url") or kwargs.get("video_id")
                    if not target:
                        return self._make_result(
                            False, "youtube", action, start_time,
                            error="Missing required argument 'url' or 'video_id'"
                        )
                    info = ydl.extract_info(target, download=False)
                    title = info.get("title", "Untitled")
                    channel = info.get("uploader", "Unknown channel")
                    views = info.get("view_count", 0)
                    desc = info.get("description", "")
                    duration = info.get("duration", 0)
                    upload_date = info.get("upload_date", "Unknown")

                    markdown_output = (
                        f"# {title}\n\n"
                        f"**Channel:** {channel} | **Views:** {views:,} | **Upload Date:** {upload_date}\n"
                        f"**Duration:** {duration}s | **URL:** {target}\n\n"
                        f"## Description\n\n{desc}"
                    )
                    data = {
                        "id": info.get("id"),
                        "title": title,
                        "channel": channel,
                        "view_count": views,
                        "duration": duration,
                        "description": desc,
                        "tags": info.get("tags", []),
                    }
                    return self._make_result(
                        True, "youtube", action, start_time,
                        data=data,
                        markdown=markdown_output,
                        raw=json.dumps(data, indent=2, default=str),
                        metadata={"video_id": info.get("id")}
                    )

        except Exception as e:
            return self._make_result(
                False, "youtube", action, start_time,
                error=f"yt-dlp execution failed: {str(e)}"
            )
