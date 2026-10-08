"""XiaoHongShu (小红书) Web and Note extractor backend."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Optional, Tuple
from neteyes.auth import get_platform_auth_status
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.cookies import load_platform_cookies
from neteyes.utils.http import get_http_client


def extract_xhs_note_id(url_or_id: str) -> Optional[str]:
    """Extract Xiaohongshu note ID (24-char hex string)."""
    url_or_id = url_or_id.strip()
    match = re.search(r"([a-f0-9]{24})", url_or_id)
    if match:
        return match.group(1)
    return None


class XhsWebBackend(BaseBackend):
    id = "xhs_web"
    name = "XiaoHongShu Web Adapter"
    priority = 10
    description = "Extracts Xiaohongshu notes, tags, images, and engagement with browser session cookies"
    backend_type = BackendType.DIRECT_API
    requires_auth = True
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        auth = get_platform_auth_status("xhs")
        if not auth.get("has_cookies"):
            return (
                HealthStatus.REQUIRES_AUTH,
                "XHS requires session cookie (a1 or web_session). Run: neteyes auth xhs --import cookies.json"
            )
        return HealthStatus.HEALTHY, f"XHS session cookies configured ({auth.get('cookie_count')} cookies)"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        target = kwargs.get("url") or kwargs.get("note_id") or ""
        note_id = extract_xhs_note_id(target) if target else None
        if note_id:
            return f'curl -sL "https://www.xiaohongshu.com/explore/{note_id}"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        target = kwargs.get("url") or kwargs.get("note_id")
        if not target:
            return self._make_result(
                False, "xhs", action, start_time,
                error="Missing required argument 'url' or 'note_id'"
            )

        note_id = extract_xhs_note_id(target)
        if not note_id:
            return self._make_result(
                False, "xhs", action, start_time,
                error=f"Could not parse valid Xiaohongshu note ID from '{target}'"
            )

        cookies = load_platform_cookies("xhs")
        client = get_http_client(
            platform="xhs",
            timeout=20.0,
            extra_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Referer": "https://www.xiaohongshu.com/",
            }
        )

        try:
            url = f"https://www.xiaohongshu.com/explore/{note_id}"
            resp = client.get(url)
            html = resp.text

            # Parse window.__INITIAL_STATE__ JSON embedded in page
            state_match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});</script>", html, re.DOTALL)
            if state_match:
                raw_json = state_match.group(1).replace("undefined", "null")
                state_data = json.loads(raw_json)
                note_data = (
                    state_data.get("note", {}).get("noteDetailMap", {}).get(note_id, {}).get("note", {})
                )

                if note_data:
                    title = note_data.get("title", "Untitled Note")
                    desc = note_data.get("desc", "")
                    user = note_data.get("user", {})
                    nickname = user.get("nickname", "Unknown")
                    liked_count = note_data.get("likedCount", 0)
                    collected_count = note_data.get("collectedCount", 0)
                    image_list = [img.get("urlDefault", "") for img in note_data.get("imageList", [])]

                    img_md = "\n".join([f"- ![]({img_url})" for img_url in image_list if img_url])
                    markdown = (
                        f"# 小红书: {title}\n\n"
                        f"**作者:** {nickname} | **点赞:** {liked_count} | **收藏:** {collected_count}\n"
                        f"**链接:** {url}\n\n"
                        f"## 正文内容\n\n{desc}\n\n"
                        f"## 图片 ({len(image_list)})\n\n{img_md}"
                    )
                    data = {
                        "note_id": note_id,
                        "title": title,
                        "author": nickname,
                        "content": desc,
                        "likes": liked_count,
                        "collected": collected_count,
                        "images": image_list,
                    }
                    return self._make_result(
                        True, "xhs", action, start_time,
                        data=data,
                        markdown=markdown,
                        metadata={"note_id": note_id}
                    )

            # Fallback if unauthenticated / anti-crawl block
            if "登录" in html or resp.status_code in (401, 403, 302):
                return self._make_result(
                    False, "xhs", action, start_time,
                    error="Xiaohongshu requires active login session. Run 'neteyes auth xhs --import cookies.json'"
                )

            return self._make_result(
                False, "xhs", action, start_time,
                error="Could not parse note data from Xiaohongshu response (page structure changed or anti-crawl active)."
            )

        except Exception as e:
            return self._make_result(
                False, "xhs", action, start_time,
                error=f"Xiaohongshu request failed: {str(e)}"
            )
