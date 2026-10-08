"""Reddit channel specification."""

from __future__ import annotations

from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.reddit import PrawBackend, RedditJsonBackend
from neteyes.models import ActionSpec, ChannelSpec


class RedditChannel:
    id = "reddit"
    name = "Reddit"
    description = "Subreddits, hot/new posts, discussion threads, comments, and search"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(
                name="sub",
                description="List posts in a subreddit",
                parameters={
                    "subreddit": "Subreddit name (e.g. 'python', 'localllama')",
                    "limit": "Number of posts (default: 10)",
                    "sort": "hot, new, top (default: hot)",
                },
                example_args=["python"],
            ),
            ActionSpec(
                name="post",
                description="Read a specific post along with its top comments",
                parameters={"url": "Reddit post URL"},
                example_args=["https://www.reddit.com/r/Python/comments/16..."],
            ),
            ActionSpec(
                name="search",
                description="Search across Reddit for posts matching a query",
                parameters={
                    "query": "Search query keywords",
                    "limit": "Max results (default: 10)",
                },
                example_args=["agentic workflows"],
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
            RedditJsonBackend(),  # Priority 10: Zero-config public .json endpoint
            PrawBackend(),        # Priority 20: Official PRAW API wrapper (requires credentials)
        ]
