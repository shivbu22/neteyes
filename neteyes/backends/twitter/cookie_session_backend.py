"""Twitter Cookie Session Backend for authenticated timelines and search."""

from __future__ import annotations

import json
import time
from typing import Any, Optional, Tuple
from neteyes.auth import get_platform_auth_status
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.cookies import load_platform_cookies
from neteyes.utils.http import get_http_client


class TwitterCookieSessionBackend(BaseBackend):
    id = "twitter_session"
    name = "Twitter Authenticated Session"
    priority = 20
    description = "Authenticated session client utilizing local browser cookies (auth_token & ct0)"
    backend_type = BackendType.DIRECT_API
    requires_auth = True
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        auth_status = get_platform_auth_status("twitter")
        if not auth_status.get("has_cookies"):
            return (
                HealthStatus.REQUIRES_AUTH,
                "No Twitter cookies configured. Import via 'neteyes auth twitter --import cookies.json'"
            )
        missing = auth_status.get("missing_keys", [])
        if missing:
            return (
                HealthStatus.DEGRADED,
                f"Twitter cookies present but missing required session keys: {', '.join(missing)}"
            )
        return HealthStatus.HEALTHY, f"Twitter session active ({auth_status.get('cookie_count')} cookies)"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        cookies = load_platform_cookies("twitter")
        if not cookies or "auth_token" not in cookies:
            return self._make_result(
                False, "twitter", action, start_time,
                error="Twitter session cookies missing. Use 'neteyes auth twitter --import <file>' first."
            )

        ct0 = cookies.get("ct0", "")
        headers = {
            "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "x-csrf-token": ct0,
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "Referer": "https://x.com/",
        }

        try:
            client = get_http_client(platform="twitter", timeout=20.0, extra_headers=headers)
            target_user = kwargs.get("user") or kwargs.get("username")
            if target_user:
                # Query user profile
                url = f"https://api.x.com/1.1/users/show.json?screen_name={target_user}"
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                name = data.get("name", target_user)
                desc = data.get("description", "")
                followers = data.get("followers_count", 0)
                statuses = data.get("statuses_count", 0)

                markdown = (
                    f"# Twitter Profile: {name} (@{target_user})\n\n"
                    f"**Followers:** {followers:,} | **Total Tweets:** {statuses:,}\n\n"
                    f"**Bio:**\n{desc}\n"
                )
                return self._make_result(
                    True, "twitter", action, start_time,
                    data=data,
                    markdown=markdown,
                    raw=json.dumps(data, indent=2),
                    metadata={"screen_name": target_user}
                )

            return self._make_result(
                False, "twitter", action, start_time,
                error="Action currently requires 'username' parameter for Twitter session adapter."
            )
        except Exception as e:
            return self._make_result(
                False, "twitter", action, start_time,
                error=f"Twitter session request failed: {str(e)}"
            )
