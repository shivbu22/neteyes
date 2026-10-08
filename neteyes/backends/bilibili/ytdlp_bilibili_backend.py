"""yt-dlp adapter for Bilibili videos."""

from __future__ import annotations

import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus


class YtDlpBilibiliBackend(BaseBackend):
    id = "ytdlp_bilibili"
    name = "yt-dlp (Bilibili Extractor)"
    priority = 20
    description = "yt-dlp extractor for Bilibili video streams and subtitles"
    backend_type = BackendType.HYBRID
    requires_auth = False
    dependencies = ["yt-dlp"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        if self.is_python_module_available("yt_dlp") or self.is_binary_available("yt-dlp"):
            return HealthStatus.HEALTHY, "yt-dlp is available for Bilibili extraction"
        return HealthStatus.MISSING_DEPENDENCY, "yt-dlp not installed"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        target = kwargs.get("bvid") or kwargs.get("url") or ""
        if target:
            url = target if target.startswith("http") else f"https://www.bilibili.com/video/{target}"
            return f'yt-dlp --dump-json --skip-download "{url}"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        try:
            import yt_dlp
        except ImportError:
            return self._make_result(
                False, "bilibili", action, start_time,
                error="yt-dlp Python library is not installed."
            )

        target = kwargs.get("bvid") or kwargs.get("url")
        if not target:
            return self._make_result(
                False, "bilibili", action, start_time,
                error="Missing required argument 'bvid' or 'url'"
            )

        url = target if target.startswith("http") else f"https://www.bilibili.com/video/{target}"

        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "Untitled")
                uploader = info.get("uploader", "Unknown")
                desc = info.get("description", "")
                markdown = f"# {title} (Bilibili via yt-dlp)\n\n**Uploader:** {uploader}\n\n{desc}"
                return self._make_result(
                    True, "bilibili", action, start_time,
                    data=info,
                    markdown=markdown,
                    metadata={"url": url}
                )
        except Exception as e:
            return self._make_result(
                False, "bilibili", action, start_time,
                error=f"yt-dlp Bilibili extraction failed: {str(e)}"
            )
