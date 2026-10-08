"""YouTube Transcript API backend."""

from __future__ import annotations

import re
import time
from typing import Any, List, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus


def extract_youtube_video_id(url_or_id: str) -> Optional[str]:
    """Extract 11-character video ID from YouTube URL or raw ID."""
    if len(url_or_id) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", url_or_id):
        return url_or_id
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/live\/|\/shorts\/)([A-Za-z0-9_-]{11})",
        r"(?:watch\?v=)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None


class YouTubeTranscriptBackend(BaseBackend):
    id = "youtube_transcript"
    name = "YouTube Transcript API"
    priority = 10
    description = "Ultra-fast direct transcript and closed-caption extractor with timestamps"
    backend_type = BackendType.PYTHON_MODULE
    requires_auth = False
    dependencies = ["youtube-transcript-api"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        if self.is_python_module_available("youtube_transcript_api"):
            return HealthStatus.HEALTHY, "youtube-transcript-api is installed and ready"
        return HealthStatus.MISSING_DEPENDENCY, "youtube-transcript-api not installed. Run: pip install youtube-transcript-api"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        target = kwargs.get("url") or kwargs.get("video_id") or ""
        video_id = extract_youtube_video_id(target) if target else None
        if action in ("transcript", "subtitles") and video_id:
            if self.is_binary_available("youtube_transcript_api"):
                return f"youtube_transcript_api {video_id} --format json"
            return f"python -m youtube_transcript_api {video_id} --format json"
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        target = kwargs.get("url") or kwargs.get("video_id") or ""
        if not target:
            return self._make_result(
                False, "youtube", action, start_time,
                error="Missing required argument 'url' or 'video_id'"
            )

        video_id = extract_youtube_video_id(target)
        if not video_id:
            return self._make_result(
                False, "youtube", action, start_time,
                error=f"Could not parse valid YouTube video ID from '{target}'"
            )

        if action not in ("transcript", "subtitles", "extract"):
            return self._make_result(
                False, "youtube", action, start_time,
                error=f"Unsupported action '{action}' for YouTubeTranscriptBackend. Supported: transcript, subtitles"
            )

        languages = kwargs.get("languages", ["en", "zh-Hans", "zh-Hant", "es", "ja"])
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)

            # Format into clean structured lines with timestamp [MM:SS]
            formatted_lines = []
            full_text_parts = []
            for item in transcript_list:
                sec = int(item.get("start", 0))
                m, s = divmod(sec, 60)
                h, m = divmod(m, 60)
                ts = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                text = item.get("text", "").strip()
                formatted_lines.append(f"[{ts}] {text}")
                full_text_parts.append(text)

            combined_text = " ".join(full_text_parts)
            transcript_md = "\n".join(formatted_lines)
            markdown_output = (
                f"# YouTube Video Transcript: `{video_id}`\n\n"
                f"**Video URL:** https://www.youtube.com/watch?v=*{video_id}*\n"
                f"**Total Segments:** {len(transcript_list)}\n\n"
                f"## Timestamped Transcript\n\n{transcript_md}\n\n"
                f"## Full Text Summary\n\n{combined_text}"
            )

            data = {
                "video_id": video_id,
                "segments": transcript_list,
                "full_text": combined_text,
                "segment_count": len(transcript_list),
            }
            return self._make_result(
                True, "youtube", action, start_time,
                data=data,
                markdown=markdown_output,
                raw=combined_text,
                metadata={"video_id": video_id}
            )
        except Exception as e:
            return self._make_result(
                False, "youtube", action, start_time,
                error=f"Transcript extraction failed: {str(e)}"
            )
