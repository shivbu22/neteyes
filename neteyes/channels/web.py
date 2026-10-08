"""Web page channel specification."""

from __future__ import annotations

from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.web import DirectReadabilityBackend, JinaReaderBackend, TrafilaturaBackend
from neteyes.models import ActionSpec, ChannelSpec


class WebChannel:
    id = "web"
    name = "Web Pages"
    description = "Clean markdown extraction and boilerplate stripping from any public URL"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(
                name="extract",
                description="Extract clean readability markdown from a web page URL",
                parameters={"url": "Target web page URL (http/https)"},
                example_args=["https://news.ycombinator.com"],
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
            TrafilaturaBackend(),       # Priority 10: Best local HTML cleaning & noise removal
            JinaReaderBackend(),        # Priority 20: Cloud reader, executes client JS / SPAs
            DirectReadabilityBackend(), # Priority 30: Zero-dependency native HTTP fallback
        ]
