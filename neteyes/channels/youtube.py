"""YouTube channel specification."""

from __future__ import annotations

from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.youtube import (
    YouTubeDirectBackend,
    YouTubeTranscriptBackend,
    YtDlpBackend,
)
from neteyes.models import ActionSpec, ChannelSpec


class YouTubeChannel:
    id = "youtube"
    name = "YouTube"
    description = "Video subtitles, closed-captions, search, and metadata extraction"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(
                name="transcript",
                description="Extract timestamped transcript and full text from a video",
                parameters={
                    "url": "YouTube video URL or 11-char ID",
                    "languages": "Optional comma-separated language preference list",
                },
                example_args=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
            ),
            ActionSpec(
                name="search",
                description="Search YouTube videos and return top results with metadata",
                parameters={
                    "query": "Search query keyword",
                    "limit": "Max results to return (default: 5)",
                },
                example_args=["AI agents 2026"],
            ),
            ActionSpec(
                name="info",
                description="Extract video details, title, views, channel, and description",
                parameters={"url": "YouTube video URL or 11-char ID"},
                example_args=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
            ),
        ]
        return ChannelSpec(
            id=cls.id,
            name=cls.name,
            description=cls.description,
            actions=actions,
            backends=backends,
            login_walled=cls.login_walled,
            zero_config=cls.zero_config,
        )

    @classmethod
    def get_backends(cls) -> List[BaseBackend]:
        """Ordered list of backends: Primary -> Fallbacks."""
        return [
            YouTubeTranscriptBackend(),  # Priority 10: Fastest dedicated transcript API
            YtDlpBackend(),              # Priority 20: yt-dlp metadata, chapters, search
            YouTubeDirectBackend(),      # Priority 30: Zero-dependency public oEmbed fallback
        ]
