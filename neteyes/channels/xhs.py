"""XiaoHongShu (小红书) channel specification."""

from __future__ import annotations

from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.xhs import XhsShortlinkBackend, XhsWebBackend
from neteyes.models import ActionSpec, ChannelSpec


class XhsChannel:
    id = "xhs"
    name = "XiaoHongShu (小红书)"
    description = "Notes, lifestyle posts, media images, and engagement stats (requires session cookies)"
    login_walled = True
    zero_config = False

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(
                name="note",
                description="Extract Xiaohongshu note content, images, author, and engagement",
                parameters={"url": "Note URL, note ID (24-hex), or mobile share shortlink"},
                example_args=["https://www.xiaohongshu.com/explore/65e9b..."],
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
            XhsWebBackend(),        # Priority 10: Web page + initial state JSON parser
            XhsShortlinkBackend(),  # Priority 20: Mobile shortlink resolver
        ]
