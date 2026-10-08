"""Web search channel specification."""

from __future__ import annotations

from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.search import DuckDuckGoBackend, SearxngBackend
from neteyes.models import ActionSpec, ChannelSpec


class SearchChannel:
    id = "search"
    name = "Web Search (Free)"
    description = "Zero-config web search with snippets and instant answer retrieval"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(
                name="query",
                description="Search the live web for keywords and return top links & snippets",
                parameters={
                    "query": "Search query keywords",
                    "limit": "Max results to return (default: 10)",
                },
                example_args=["latest AI agent frameworks"],
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
            DuckDuckGoBackend(),  # Priority 10: Free DuckDuckGo search (Python library or Lite HTML)
            SearxngBackend(),     # Priority 20: Open-source SearXNG meta-search fallback
        ]
