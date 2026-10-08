"""XiaoHongShu shortlink resolver backend."""

from __future__ import annotations

import time
from typing import Any, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.backends.xhs.xhs_web_backend import XhsWebBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


class XhsShortlinkBackend(BaseBackend):
    id = "xhs_shortlink"
    name = "Xiaohongshu Shortlink Resolver"
    priority = 20
    description = "Resolves mobile share shortlinks (xhslink.com) and extracts full note"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        return HealthStatus.HEALTHY, "XHS shortlink resolver operational"

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        url = kwargs.get("url", "")
        if not url:
            return self._make_result(
                False, "xhs", action, start_time,
                error="Missing required argument 'url'"
            )

        client = get_http_client(platform="xhs", follow_redirects=True)
        try:
            resp = client.get(url)
            final_url = str(resp.url)
            kwargs["url"] = final_url

            # Delegate to web backend with the resolved URL
            web_backend = XhsWebBackend()
            return web_backend.execute(action, **kwargs)
        except Exception as e:
            return self._make_result(
                False, "xhs", action, start_time,
                error=f"Shortlink resolution failed: {str(e)}"
            )
