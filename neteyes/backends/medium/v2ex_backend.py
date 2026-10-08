"""V2EX community backend."""

from __future__ import annotations

import json
import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


class V2exBackend(BaseBackend):
    id = "v2ex"
    name = "V2EX Community API"
    priority = 10
    description = "Public API endpoints for V2EX hot topics, latest discussions, and node posts"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        return HealthStatus.HEALTHY, "V2EX public API is available"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        if action == "hot":
            return 'curl -sL "https://www.v2ex.com/api/topics/hot.json"'
        elif action == "latest":
            return 'curl -sL "https://www.v2ex.com/api/topics/latest.json"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        client = get_http_client(platform="v2ex", timeout=15.0)

        try:
            if action in ("hot", "latest", "topics"):
                sub_endpoint = "hot" if action == "hot" else "latest"
                endpoint = f"https://www.v2ex.com/api/topics/{sub_endpoint}.json"
                resp = client.get(endpoint)
                resp.raise_for_status()
                topics = resp.json()

                limit = int(kwargs.get("limit", 10))
                items = topics[:limit]

                md_lines = [f"# V2EX Topics ({sub_endpoint.capitalize()})\n"]
                for idx, t in enumerate(items, 1):
                    title = t.get("title", "")
                    url = t.get("url", "")
                    member = t.get("member", {}).get("username", "unknown")
                    replies = t.get("replies", 0)
                    node = t.get("node", {}).get("title", "general")
                    md_lines.append(f"{idx}. [{title}]({url}) `[{node}]`")
                    md_lines.append(f"   *By:* @{member} | *Replies:* {replies}\n")

                return self._make_result(
                    True, "v2ex", action, start_time,
                    data=items,
                    markdown="\n".join(md_lines),
                    raw=json.dumps(items, indent=2, ensure_ascii=False),
                    metadata={"count": len(items)}
                )

            elif action in ("show", "topic"):
                topic_id = kwargs.get("id") or kwargs.get("topic_id")
                if not topic_id:
                    return self._make_result(
                        False, "v2ex", action, start_time,
                        error="Missing required argument 'id' for V2EX topic"
                    )
                endpoint = f"https://www.v2ex.com/api/topics/show.json?id={topic_id}"
                resp = client.get(endpoint)
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    return self._make_result(
                        False, "v2ex", action, start_time,
                        error=f"Topic {topic_id} not found"
                    )
                topic = data[0] if isinstance(data, list) else data
                title = topic.get("title", "")
                content = topic.get("content", "")
                url = topic.get("url", "")
                member = topic.get("member", {}).get("username", "unknown")

                md = (
                    f"# V2EX: {title}\n\n"
                    f"**Author:** @{member} | **Link:** {url}\n\n"
                    f"---\n\n{content}"
                )
                return self._make_result(
                    True, "v2ex", action, start_time,
                    data=topic,
                    markdown=md,
                )

            return self._make_result(
                False, "v2ex", action, start_time,
                error=f"Unsupported action '{action}' for V2EX. Supported: hot, latest, show"
            )

        except Exception as e:
            return self._make_result(
                False, "v2ex", action, start_time,
                error=f"V2EX request failed: {str(e)}"
            )
