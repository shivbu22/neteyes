"""Bilibili channel specification."""

from __future__ import annotations

from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.bilibili import BilibiliWebBackend, YtDlpBilibiliBackend
from neteyes.models import ActionSpec, ChannelSpec


class BilibiliChannel:
    id = "bilibili"
    name = "Bilibili"
    description = "Video metadata, stats (views/danmaku/coins), CC subtitles, and UP主 details"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(
                name="view",
                description="Get video details, description, statistics, and owner",
                parameters={"bvid": "Bilibili BV ID (e.g. BV1xx411c7mD) or video URL"},
                example_args=["BV1xx411c7mD"],
            ),
            ActionSpec(
                name="subtitles",
                description="Extract timestamped CC subtitles if available",
                parameters={"bvid": "Bilibili BV ID or video URL"},
                example_args=["BV1xx411c7mD"],
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
            BilibiliWebBackend(),    # Priority 10: Official public Web API (view + subtitles)
            YtDlpBilibiliBackend(),  # Priority 20: yt-dlp bilibili adapter
        ]
