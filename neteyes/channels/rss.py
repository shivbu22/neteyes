"""RSS / Atom feed channel specification."""

from __future__ import annotations

from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.rss import FeedparserBackend, XmlRssBackend
from neteyes.models import ActionSpec, ChannelSpec


class RssChannel:
    id = "rss"
    name = "RSS & Atom Feeds"
    description = "Universal feed syndication reader for blogs, newsletters, and podcasts"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(
                name="read",
                description="Fetch and parse an RSS or Atom feed into a structured digest",
                parameters={
                    "url": "Feed URL (XML/Atom/RSS)",
                    "limit": "Max entries to return (default: 10)",
                },
                example_args=["https://news.ycombinator.com/rss"],
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
            FeedparserBackend(),  # Priority 10: Full RSS/Atom parser with encoding support
            XmlRssBackend(),       # Priority 20: Built-in XML ElementTree fallback
        ]
