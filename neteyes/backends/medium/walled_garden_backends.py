"""Adapters for walled gardens (LinkedIn, Instagram, Boss直聘) and Podcasts."""

from __future__ import annotations

import json
import time
from typing import Any, Optional, Tuple
from neteyes.auth import get_platform_auth_status
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.cookies import load_platform_cookies
from neteyes.utils.http import get_http_client, simple_html_to_markdown


class LinkedInBackend(BaseBackend):
    id = "linkedin_session"
    name = "LinkedIn Profile & Company Client"
    priority = 10
    description = "LinkedIn public profile and company lookup with li_at cookie session"
    backend_type = BackendType.DIRECT_API
    requires_auth = True
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        auth = get_platform_auth_status("linkedin")
        if not auth.get("has_cookies"):
            return HealthStatus.REQUIRES_AUTH, "Missing li_at cookie. Run: neteyes auth linkedin --import cookies.json"
        return HealthStatus.HEALTHY, "LinkedIn session active"

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        url = kwargs.get("url") or kwargs.get("profile")
        if not url:
            return self._make_result(False, "linkedin", action, start_time, error="Missing 'url' or 'profile'")
        cookies = load_platform_cookies("linkedin")
        if not cookies:
            return self._make_result(
                False, "linkedin", action, start_time,
                error="LinkedIn requires active login cookie (li_at). Run 'neteyes auth linkedin --import <file>'"
            )
        try:
            client = get_http_client(platform="linkedin")
            resp = client.get(url)
            text = simple_html_to_markdown(resp.text)
            return self._make_result(True, "linkedin", action, start_time, data={"url": url}, markdown=f"# LinkedIn\n\n{text[:2000]}")
        except Exception as e:
            return self._make_result(False, "linkedin", action, start_time, error=str(e))


class InstagramBackend(BaseBackend):
    id = "instagram_session"
    name = "Instagram Web Profile Extractor"
    priority = 10
    description = "Instagram public profiles and posts with sessionid cookie"
    backend_type = BackendType.DIRECT_API
    requires_auth = True
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        auth = get_platform_auth_status("instagram")
        if not auth.get("has_cookies"):
            return HealthStatus.REQUIRES_AUTH, "Missing sessionid cookie. Run: neteyes auth instagram --import cookies.json"
        return HealthStatus.HEALTHY, "Instagram session active"

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        username = kwargs.get("username") or kwargs.get("user")
        if not username:
            return self._make_result(False, "instagram", action, start_time, error="Missing 'username'")
        cookies = load_platform_cookies("instagram")
        if not cookies:
            return self._make_result(
                False, "instagram", action, start_time,
                error="Instagram requires active login cookie (sessionid). Run 'neteyes auth instagram --import <file>'"
            )
        try:
            client = get_http_client(platform="instagram")
            resp = client.get(f"https://www.instagram.com/{username}/?__a=1&__d=dis")
            data = resp.json()
            return self._make_result(True, "instagram", action, start_time, data=data, markdown=f"# Instagram @{username}\n\n```json\n{json.dumps(data, indent=2)[:1000]}\n```")
        except Exception as e:
            return self._make_result(False, "instagram", action, start_time, error=str(e))


class BossZhipinBackend(BaseBackend):
    id = "boss_web"
    name = "Boss直聘 Job Extractor"
    priority = 10
    description = "Boss直聘 job descriptions and company info with wt2 session token"
    backend_type = BackendType.DIRECT_API
    requires_auth = True
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        auth = get_platform_auth_status("boss")
        if not auth.get("has_cookies"):
            return HealthStatus.REQUIRES_AUTH, "Missing wt2 cookie. Run: neteyes auth boss --import cookies.json"
        return HealthStatus.HEALTHY, "Boss session token configured"

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        url = kwargs.get("url")
        if not url:
            return self._make_result(False, "boss", action, start_time, error="Missing 'url'")
        cookies = load_platform_cookies("boss")
        if not cookies:
            return self._make_result(
                False, "boss", action, start_time,
                error="Boss直聘 requires wt2 session cookie. Run 'neteyes auth boss --import <file>'"
            )
        try:
            client = get_http_client(platform="boss")
            resp = client.get(url)
            text = simple_html_to_markdown(resp.text)
            return self._make_result(True, "boss", action, start_time, data={"url": url}, markdown=f"# Boss直聘\n\n{text[:2000]}")
        except Exception as e:
            return self._make_result(False, "boss", action, start_time, error=str(e))


class PodcastBackend(BaseBackend):
    id = "podcast_rss"
    name = "Podcast Feed & Audio Extractor"
    priority = 10
    description = "Parses podcast RSS feeds, show notes, and audio enclosure MP3 links"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["feedparser", "httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        return HealthStatus.HEALTHY, "Podcast RSS parser operational"

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        url = kwargs.get("url")
        if not url:
            return self._make_result(False, "podcast", action, start_time, error="Missing 'url'")
        try:
            import feedparser
            client = get_http_client(platform="podcast")
            resp = client.get(url)
            feed = feedparser.parse(resp.text)
            title = feed.feed.get("title", "Podcast")
            episodes = []
            md_lines = [f"# Podcast: {title}\n"]
            for ep in feed.entries[:5]:
                ep_title = ep.get("title", "Untitled Episode")
                enclosures = ep.get("enclosures", [])
                audio_url = enclosures[0].get("href", "") if enclosures else ""
                md_lines.append(f"- **{ep_title}**\n  [Audio Stream]({audio_url})\n")
                episodes.append({"title": ep_title, "audio_url": audio_url})
            return self._make_result(
                True, "podcast", action, start_time,
                data=episodes,
                markdown="\n".join(md_lines)
            )
        except Exception as e:
            return self._make_result(False, "podcast", action, start_time, error=str(e))
