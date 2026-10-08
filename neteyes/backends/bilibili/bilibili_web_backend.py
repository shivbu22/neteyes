"""Bilibili Web API backend."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


def extract_bvid(target: str) -> Optional[str]:
    """Extract Bilibili BV ID (e.g. BV1xx411c7mD)."""
    match = re.search(r"(BV[a-zA-Z0-9]{10})", target)
    if match:
        return match.group(1)
    return None


class BilibiliWebBackend(BaseBackend):
    id = "bilibili_web"
    name = "Bilibili Public Web API"
    priority = 10
    description = "Public API endpoints for video info, subtitles, and search with optional SESSDATA cookie"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        try:
            client = get_http_client(platform="bilibili", timeout=5.0)
            resp = client.get("https://api.bilibili.com/x/web-interface/view?bvid=BV1xx411c7mD")
            if resp.status_code == 200 and resp.json().get("code") == 0:
                return HealthStatus.HEALTHY, "Bilibili Web API is responsive and operational"
            return HealthStatus.DEGRADED, f"Bilibili API returned non-zero code: {resp.text[:100]}"
        except Exception as e:
            return HealthStatus.UNAVAILABLE, f"Bilibili API unreachable: {str(e)}"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        target = kwargs.get("bvid") or kwargs.get("url") or ""
        bvid = extract_bvid(target) if target else None
        if bvid:
            return f'curl -sL "https://api.bilibili.com/x/web-interface/view?bvid={bvid}"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        client = get_http_client(
            platform="bilibili",
            timeout=15.0,
            extra_headers={
                "Referer": "https://www.bilibili.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            }
        )

        try:
            if action in ("view", "info", "extract"):
                target = kwargs.get("bvid") or kwargs.get("url")
                if not target:
                    return self._make_result(
                        False, "bilibili", action, start_time,
                        error="Missing required argument 'bvid' or 'url'"
                    )
                bvid = extract_bvid(target)
                if not bvid:
                    return self._make_result(
                        False, "bilibili", action, start_time,
                        error=f"Could not parse valid Bilibili BV ID from '{target}'"
                    )

                data = {}
                title = "Untitled"
                owner = "Unknown"
                desc = ""
                views = 0
                danmaku = 0
                coins = 0
                cid = 0

                # 1. Try public API first
                try:
                    resp = client.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
                    if resp.status_code == 200:
                        res_json = resp.json()
                        if res_json.get("code") == 0:
                            data = res_json.get("data", {})
                            title = data.get("title", "Untitled")
                            owner = data.get("owner", {}).get("name", "Unknown")
                            desc = data.get("desc", "")
                            stat = data.get("stat", {})
                            views = stat.get("view", 0)
                            danmaku = stat.get("danmaku", 0)
                            coins = stat.get("coin", 0)
                            cid = data.get("cid", 0)
                except Exception:
                    pass

                # 2. Resilient fallback to video web page INITIAL_STATE
                if not data:
                    page_url = f"https://www.bilibili.com/video/{bvid}/"
                    page_resp = client.get(page_url)
                    state_match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});", page_resp.text)
                    if state_match:
                        raw_state = state_match.group(1).replace("undefined", "null")
                        state_json = json.loads(raw_state)
                        vdata = state_json.get("videoData", {})
                        if vdata:
                            title = vdata.get("title", "Untitled")
                            owner = vdata.get("owner", {}).get("name", "Unknown")
                            desc = vdata.get("desc", "")
                            stat = vdata.get("stat", {})
                            views = stat.get("view", 0)
                            danmaku = stat.get("danmaku", 0)
                            coins = stat.get("coin", 0)
                            cid = vdata.get("cid", 0)
                            data = vdata

                if not data:
                    return self._make_result(
                        False, "bilibili", action, start_time,
                        error=f"Could not retrieve video details for Bilibili ID '{bvid}'"
                    )

                markdown = (
                    f"# Bilibili: {title} (`{bvid}`)\n\n"
                    f"**UP主:** {owner} | **Views:** {views:,} | **Danmaku:** {danmaku:,} | **Coins:** {coins:,}\n"
                    f"**Link:** https://www.bilibili.com/video/{bvid}\n\n"
                    f"## Description\n\n{desc}\n"
                )

                result_data = {
                    "bvid": bvid,
                    "cid": cid,
                    "title": title,
                    "owner": owner,
                    "views": views,
                    "danmaku": danmaku,
                    "coins": coins,
                    "description": desc,
                }
                return self._make_result(
                    True, "bilibili", action, start_time,
                    data=result_data,
                    markdown=markdown,
                    raw=json.dumps(result_data, indent=2, ensure_ascii=False),
                    metadata={"bvid": bvid}
                )

            elif action == "search":
                query = kwargs.get("query", "")
                if not query:
                    return self._make_result(
                        False, "bilibili", action, start_time,
                        error="Missing required argument 'query' for Bilibili search"
                    )
                limit = int(kwargs.get("limit", 5))

                # Use public search endpoint
                endpoint = f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={query}&page=1"
                resp = client.get(endpoint)
                items = []
                if resp.status_code == 200:
                    try:
                        sdata = resp.json().get("data", {}).get("result", [])
                        for cat in sdata:
                            if cat.get("result_type") == "video":
                                items = cat.get("data", [])[:limit]
                                break
                    except Exception:
                        pass

                md_lines = [f"# Bilibili Search: `{query}`\n"]
                for idx, it in enumerate(items, 1):
                    raw_t = it.get("title", "Untitled")
                    clean_t = re.sub(r"<[^>]+>", "", raw_t)
                    author = it.get("author", "unknown")
                    bvid = it.get("bvid", "")
                    link = f"https://www.bilibili.com/video/{bvid}"
                    md_lines.append(f"{idx}. **[{clean_t}]({link})** (UP主: {author})")

                return self._make_result(
                    True, "bilibili", action, start_time,
                    data=items,
                    markdown="\n".join(md_lines),
                    metadata={"query": query, "count": len(items)}
                )

            elif action in ("subtitles", "subtitle", "cc"):
                target = kwargs.get("bvid") or kwargs.get("url")
                bvid = extract_bvid(target) if target else None
                if not bvid:
                    return self._make_result(
                        False, "bilibili", action, start_time,
                        error="Missing valid 'bvid' or 'url' for subtitle extraction"
                    )

                # Fetch view first to get cid
                view_resp = client.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
                view_resp.raise_for_status()
                vdata = view_resp.json().get("data", {})
                cid = vdata.get("cid")

                # Fetch player v2
                player_url = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
                player_resp = client.get(player_url)
                player_resp.raise_for_status()
                pdata = player_resp.json().get("data", {})
                subtitles_list = pdata.get("subtitle", {}).get("subtitles", [])

                if not subtitles_list:
                    return self._make_result(
                        True, "bilibili", action, start_time,
                        data=[],
                        markdown=f"# Bilibili Subtitles (`{bvid}`)\n\nNo CC subtitles found for this video.",
                        metadata={"bvid": bvid}
                    )

                sub_url = subtitles_list[0].get("subtitle_url", "")
                if sub_url.startswith("//"):
                    sub_url = "https:" + sub_url

                sub_content_resp = client.get(sub_url)
                sub_body = sub_content_resp.json().get("body", [])

                lines = []
                for item in sub_body:
                    start_sec = item.get("from", 0)
                    m, s = divmod(int(start_sec), 60)
                    ts = f"{m:02d}:{s:02d}"
                    lines.append(f"[{ts}] {item.get('content', '')}")

                md_out = f"# Bilibili Subtitles (`{bvid}`)\n\n" + "\n".join(lines)
                return self._make_result(
                    True, "bilibili", action, start_time,
                    data=sub_body,
                    markdown=md_out,
                    metadata={"bvid": bvid, "count": len(sub_body)}
                )

            return self._make_result(
                False, "bilibili", action, start_time,
                error=f"Unsupported action '{action}' for Bilibili. Supported: view, subtitles"
            )

        except Exception as e:
            return self._make_result(
                False, "bilibili", action, start_time,
                error=f"Bilibili API failed: {str(e)}"
            )
