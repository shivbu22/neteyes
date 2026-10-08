"""Resilient HTTP client utilities for NetEyes."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional
import httpx
from neteyes.config import load_config
from neteyes.utils.cookies import load_platform_cookies

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 NetEyes/0.1.0"
)


def get_default_headers(platform: Optional[str] = None) -> Dict[str, str]:
    """Build standard browser-like headers."""
    cfg = load_config()
    ua = cfg.get("user_agent", DEFAULT_USER_AGENT)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
    return headers


def get_http_client(
    platform: Optional[str] = None,
    timeout: Optional[float] = None,
    follow_redirects: bool = True,
    extra_headers: Optional[Dict[str, str]] = None,
) -> httpx.Client:
    """Create an httpx client pre-loaded with configuration and cookies."""
    cfg = load_config()
    to = timeout or float(cfg.get("timeout_seconds", 15))
    headers = get_default_headers(platform)
    if extra_headers:
        headers.update(extra_headers)

    cookies = {}
    if platform:
        cookies = load_platform_cookies(platform)

    # Use rotating proxy pool if configured, else static fallback
    from neteyes.utils.proxy import get_next_proxy
    proxy = get_next_proxy(rotate=True) or cfg.get("proxy")

    return httpx.Client(
        headers=headers,
        cookies=cookies,
        timeout=to,
        follow_redirects=follow_redirects,
        proxy=proxy,
        verify=True,
    )


def simple_html_to_markdown(html_content: str) -> str:
    """Zero-dependency HTML to clean Markdown fallback converter."""
    text = html_content

    # Remove script, style, nav, footer, header tags and their contents
    text = re.sub(r"<(script|style|nav|footer|header|aside|svg|iframe)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Convert headings
    text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<h4[^>]*>(.*?)</h4>", r"\n#### \1\n", text, flags=re.IGNORECASE)

    # Convert links
    text = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r"[\2](\1)", text, flags=re.IGNORECASE)

    # Convert formatting
    text = re.sub(r"<(b|strong)[^>]*>(.*?)</\1>", r"**\2**", text, flags=re.IGNORECASE)
    text = re.sub(r"<(i|em)[^>]*>(.*?)</\1>", r"*\2*", text, flags=re.IGNORECASE)
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.IGNORECASE)
    text = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", text, flags=re.DOTALL | re.IGNORECASE)

    # Convert lists and paragraphs
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\n\1\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", r"\n", text, flags=re.IGNORECASE)

    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Unescape common HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines()]
    clean_text = "\n".join(line for line in lines if line)
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)
    return clean_text.strip()
