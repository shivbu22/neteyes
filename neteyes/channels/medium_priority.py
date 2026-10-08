"""Medium priority channels: V2EX, Xueqiu, LinkedIn, Instagram, Boss直聘, Podcast."""

from __future__ import annotations

from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.medium import (
    BossZhipinBackend,
    InstagramBackend,
    LinkedInBackend,
    PodcastBackend,
    V2exBackend,
    XueqiuBackend,
)
from neteyes.models import ActionSpec, ChannelSpec


class V2exChannel:
    id = "v2ex"
    name = "V2EX"
    description = "Chinese developer community hot topics and discussion threads"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(name="hot", description="Get current hot topics on V2EX", parameters={"limit": "Number of topics"}),
            ActionSpec(name="show", description="Show a specific V2EX topic", parameters={"id": "Topic ID numeric"}),
        ]
        return ChannelSpec(id=cls.id, name=cls.name, description=cls.description, actions=actions, backends=backends)

    @classmethod
    def get_backends(cls) -> List[BaseBackend]:
        return [V2exBackend()]


class XueqiuChannel:
    id = "xueqiu"
    name = "Xueqiu (雪球)"
    description = "Chinese stock market quotes and investor discussions"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(name="quote", description="Get stock price & valuation", parameters={"symbol": "Stock code (e.g. SH600519, BABA)"}),
            ActionSpec(name="search", description="Search financial posts", parameters={"query": "Search query"}),
        ]
        return ChannelSpec(id=cls.id, name=cls.name, description=cls.description, actions=actions, backends=backends)

    @classmethod
    def get_backends(cls) -> List[BaseBackend]:
        return [XueqiuBackend()]


class LinkedInChannel:
    id = "linkedin"
    name = "LinkedIn"
    description = "Professional profiles and company pages (requires session cookies)"
    login_walled = True
    zero_config = False

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(name="profile", description="Fetch public profile", parameters={"url": "Profile URL"}),
        ]
        return ChannelSpec(id=cls.id, name=cls.name, description=cls.description, actions=actions, backends=backends, login_walled=True, zero_config=False)

    @classmethod
    def get_backends(cls) -> List[BaseBackend]:
        return [LinkedInBackend()]


class InstagramChannel:
    id = "instagram"
    name = "Instagram"
    description = "Instagram public profiles and posts (requires session cookies)"
    login_walled = True
    zero_config = False

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(name="user", description="Fetch user profile info", parameters={"username": "Instagram username"}),
        ]
        return ChannelSpec(id=cls.id, name=cls.name, description=cls.description, actions=actions, backends=backends, login_walled=True, zero_config=False)

    @classmethod
    def get_backends(cls) -> List[BaseBackend]:
        return [InstagramBackend()]


class BossChannel:
    id = "boss"
    name = "Boss直聘"
    description = "Job recruitment postings and company profiles (requires session cookies)"
    login_walled = True
    zero_config = False

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(name="job", description="Extract job posting", parameters={"url": "Job posting URL"}),
        ]
        return ChannelSpec(id=cls.id, name=cls.name, description=cls.description, actions=actions, backends=backends, login_walled=True, zero_config=False)

    @classmethod
    def get_backends(cls) -> List[BaseBackend]:
        return [BossZhipinBackend()]


class PodcastChannel:
    id = "podcast"
    name = "Podcasts"
    description = "Podcast RSS episode listings, show notes, and audio stream links"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(name="feed", description="Extract podcast episodes and audio URLs", parameters={"url": "Podcast RSS feed URL"}),
        ]
        return ChannelSpec(id=cls.id, name=cls.name, description=cls.description, actions=actions, backends=backends)

    @classmethod
    def get_backends(cls) -> List[BaseBackend]:
        return [PodcastBackend()]
