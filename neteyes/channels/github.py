"""GitHub channel specification."""

from __future__ import annotations

from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.github import GhCliBackend, GitHubApiBackend
from neteyes.models import ActionSpec, ChannelSpec


class GitHubChannel:
    id = "github"
    name = "GitHub"
    description = "Repositories, issues, pull requests, releases, and README inspection"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(
                name="repo",
                description="View repository overview, stars, forks, and description",
                parameters={"repo": "Repository in owner/repo format"},
                example_args=["torvalds/linux"],
            ),
            ActionSpec(
                name="readme",
                description="Fetch and render repository README markdown",
                parameters={"repo": "Repository in owner/repo format"},
                example_args=["astral-sh/uv"],
            ),
            ActionSpec(
                name="issues",
                description="List latest open issues in a repository",
                parameters={
                    "repo": "Repository in owner/repo format",
                    "limit": "Max issues to retrieve (default: 10)",
                },
                example_args=["psf/requests"],
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
            GhCliBackend(),      # Priority 10: Upstream official gh CLI binary
            GitHubApiBackend(),  # Priority 20: Direct REST API client (with or without token)
        ]
