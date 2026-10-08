"""Twitter / X channel specification."""

from __future__ import annotations

from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.twitter import TwitterCookieSessionBackend, TwitterSyndicationBackend
from neteyes.models import ActionSpec, ChannelSpec


class TwitterChannel:
    id = "twitter"
    name = "Twitter / X"
    description = "Tweets, threads, metrics, and profiles with zero-login syndication and session cookie support"
    login_walled = True
    zero_config = False

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(
                name="tweet",
                description="Extract single tweet or thread content, metrics, and media without login",
                parameters={"url": "Tweet URL or numeric status ID"},
                example_args=["https://x.com/OpenAI/status/1780287739502756019"],
            ),
            ActionSpec(
                name="user",
                description="Lookup user profile info and stats (requires session cookies)",
                parameters={"username": "Twitter username / handle"},
                example_args=["sama"],
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
            TwitterSyndicationBackend(),    # Priority 10: Zero-login syndication CDN (single tweets, media)
            TwitterCookieSessionBackend(),  # Priority 20: Authenticated session for profiles & search
        ]
