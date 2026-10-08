"""Twitter / X Syndication API backend (Zero-login for tweets and threads)."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


def extract_tweet_id(url_or_id: str) -> Optional[str]:
    """Extract tweet ID from URL or raw ID."""
    url_or_id = url_or_id.strip()
    if url_or_id.isdigit():
        return url_or_id
    match = re.search(r"(?:twitter\.com|x\.com)/[^/]+/status/(\d+)", url_or_id)
    if match:
        return match.group(1)
    return None


class TwitterSyndicationBackend(BaseBackend):
    id = "twitter_syndication"
    name = "Twitter Public Syndication CDN"
    priority = 10
    description = "Zero-login public CDN extraction for tweets, threads, metrics, and media"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        return HealthStatus.HEALTHY, "Twitter public syndication CDN endpoint is accessible"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        target = kwargs.get("url") or kwargs.get("tweet_id") or ""
        tweet_id = extract_tweet_id(target) if target else None
        if tweet_id:
            return f'curl -sL "https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        target = kwargs.get("url") or kwargs.get("tweet_id")
        if not target:
            return self._make_result(
                False, "twitter", action, start_time,
                error="Missing required argument 'url' or 'tweet_id'"
            )

        tweet_id = extract_tweet_id(target)
        if not tweet_id:
            return self._make_result(
                False, "twitter", action, start_time,
                error=f"Could not parse valid tweet ID from '{target}'"
            )

        try:
            client = get_http_client(platform="twitter", timeout=15.0)
            url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en"
            resp = client.get(url)
            if resp.status_code == 404:
                return self._make_result(
                    False, "twitter", action, start_time,
                    error=f"Tweet {tweet_id} not found or has been deleted."
                )
            resp.raise_for_status()
            data = resp.json()

            user = data.get("user", {})
            user_name = user.get("name", "Unknown")
            screen_name = user.get("screen_name", "unknown")
            text = data.get("text", "")
            created_at = data.get("created_at", "")
            likes = data.get("favorite_count", 0)
            retweets = data.get("retweet_count", 0)

            # Extract media items
            media_list = data.get("mediaDetails", [])
            media_md = ""
            if media_list:
                media_md = "\n\n**Media:**\n"
                for media in media_list:
                    m_url = media.get("media_url_https", "")
                    m_type = media.get("type", "image")
                    media_md += f"- [{m_type.capitalize()}]({m_url})\n"

            markdown_output = (
                f"# Tweet by {user_name} (@{screen_name})\n\n"
                f"**Date:** {created_at} | **Likes:** {likes:,} | **Retweets:** {retweets:,}\n"
                f"**Link:** https://x.com/{screen_name}/status/{tweet_id}\n\n"
                f"---\n\n"
                f"{text}"
                f"{media_md}"
            )

            result_data = {
                "id": tweet_id,
                "author": f"{user_name} (@{screen_name})",
                "screen_name": screen_name,
                "text": text,
                "created_at": created_at,
                "favorite_count": likes,
                "retweet_count": retweets,
                "media": media_list,
            }
            return self._make_result(
                True, "twitter", action, start_time,
                data=result_data,
                markdown=markdown_output,
                raw=json.dumps(data, indent=2),
                metadata={"tweet_id": tweet_id}
            )
        except Exception as e:
            return self._make_result(
                False, "twitter", action, start_time,
                error=f"Twitter syndication fetch failed: {str(e)}"
            )
