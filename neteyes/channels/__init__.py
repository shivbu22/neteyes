"""Channels registry and discovery."""

from __future__ import annotations

from typing import Dict, List, Optional, Type
from neteyes.backends.base import BaseBackend
from neteyes.channels.bilibili import BilibiliChannel
from neteyes.channels.github import GitHubChannel
from neteyes.channels.medium_priority import (
    BossChannel,
    InstagramChannel,
    LinkedInChannel,
    PodcastChannel,
    V2exChannel,
    XueqiuChannel,
)
from neteyes.channels.reddit import RedditChannel
from neteyes.channels.rss import RssChannel
from neteyes.channels.search import SearchChannel
from neteyes.channels.twitter import TwitterChannel
from neteyes.channels.web import WebChannel
from neteyes.channels.xhs import XhsChannel
from neteyes.channels.youtube import YouTubeChannel
from neteyes.models import ChannelSpec

CHANNEL_REGISTRY: Dict[str, Any] = {
    "web": WebChannel,
    "youtube": YouTubeChannel,
    "twitter": TwitterChannel,
    "reddit": RedditChannel,
    "github": GitHubChannel,
    "bilibili": BilibiliChannel,
    "xhs": XhsChannel,
    "rss": RssChannel,
    "search": SearchChannel,
    "v2ex": V2exChannel,
    "xueqiu": XueqiuChannel,
    "linkedin": LinkedInChannel,
    "instagram": InstagramChannel,
    "boss": BossChannel,
    "podcast": PodcastChannel,
}

CHANNEL_ALIASES: Dict[str, str] = {
    "x": "twitter",
    "yt": "youtube",
    "gh": "github",
    "bili": "bilibili",
    "redbook": "xhs",
    "xiaohongshu": "xhs",
    "ddg": "search",
    "google": "search",
    "feed": "rss",
}


def normalize_channel_id(channel_id: str) -> str:
    """Resolve aliases into normalized channel id."""
    cid = channel_id.lower().strip()
    return CHANNEL_ALIASES.get(cid, cid)


def get_channel(channel_id: str):
    """Retrieve channel class by id or alias."""
    cid = normalize_channel_id(channel_id)
    return CHANNEL_REGISTRY.get(cid)


def list_channels() -> List[ChannelSpec]:
    """Return specs of all registered channels."""
    return [ch.get_spec() for ch in CHANNEL_REGISTRY.values()]


def get_backends_for_channel(channel_id: str) -> List[BaseBackend]:
    """Return ordered backends for a channel."""
    ch = get_channel(channel_id)
    if not ch:
        return []
    return ch.get_backends()


__all__ = [
    "CHANNEL_REGISTRY",
    "normalize_channel_id",
    "get_channel",
    "list_channels",
    "get_backends_for_channel",
]
