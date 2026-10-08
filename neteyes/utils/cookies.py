"""Cookie parsing and storage supporting Cookie-Editor JSON and Netscape formats."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from neteyes.config import get_cookies_dir


def normalize_platform_name(platform: str) -> str:
    """Normalize platform identifier (e.g. 'twitter' -> 'twitter', 'x' -> 'twitter')."""
    p = platform.lower().strip()
    aliases = {
        "x": "twitter",
        "redbook": "xhs",
        "xiaohongshu": "xhs",
        "bili": "bilibili",
        "gh": "github",
        "yt": "youtube",
    }
    return aliases.get(p, p)


def parse_cookie_editor_json(content: str) -> Dict[str, str]:
    """Parse Cookie-Editor browser extension JSON export."""
    cookies_dict: Dict[str, str] = {}
    data = json.loads(content)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "name" in item and "value" in item:
                cookies_dict[str(item["name"])] = str(item["value"])
    elif isinstance(data, dict):
        for k, v in data.items():
            cookies_dict[str(k)] = str(v)
    return cookies_dict


def parse_netscape_cookies(content: str) -> Dict[str, str]:
    """Parse Netscape/curl format cookies.txt."""
    cookies_dict: Dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            name = parts[5].strip()
            val = parts[6].strip()
            cookies_dict[name] = val
        elif "\t" in line:
            kv = line.split("\t")
            if len(kv) >= 2:
                cookies_dict[kv[0].strip()] = kv[1].strip()
    return cookies_dict


def parse_header_cookie_string(content: str) -> Dict[str, str]:
    """Parse HTTP Cookie header string ('key1=val1; key2=val2')."""
    cookies_dict: Dict[str, str] = {}
    tokens = content.split(";")
    for token in tokens:
        token = token.strip()
        if "=" in token:
            name, val = token.split("=", 1)
            cookies_dict[name.strip()] = val.strip()
    return cookies_dict


def parse_cookie_input(raw: str) -> Dict[str, str]:
    """Automatically detect and parse any cookie format."""
    raw = raw.strip()
    if not raw:
        return {}

    # Try JSON
    if raw.startswith("[") or raw.startswith("{"):
        try:
            return parse_cookie_editor_json(raw)
        except Exception:
            pass

    # Try Netscape
    if "\t" in raw and not raw.startswith("Cookie:"):
        parsed = parse_netscape_cookies(raw)
        if parsed:
            return parsed

    # Clean header prefix if present
    if raw.lower().startswith("cookie:"):
        raw = raw[7:].strip()

    # Try key=val header format
    if "=" in raw:
        return parse_header_cookie_string(raw)

    return {}


def get_cookie_file_path(platform: str) -> Path:
    """Get the JSON file path for stored platform cookies."""
    norm = normalize_platform_name(platform)
    return get_cookies_dir() / f"{norm}.json"


def save_platform_cookies(platform: str, cookies: Dict[str, str], metadata: Optional[Dict[str, Any]] = None) -> Path:
    """Save parsed cookies to disk securely in ~/.neteyes/cookies/<platform>.json."""
    norm = normalize_platform_name(platform)
    target = get_cookie_file_path(norm)
    payload = {
        "platform": norm,
        "cookie_count": len(cookies),
        "cookies": cookies,
        "metadata": metadata or {},
    }
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    try:
        import os
        os.chmod(target, 0o600)
    except Exception:
        pass
    return target


def load_platform_cookies(platform: str) -> Dict[str, str]:
    """Load stored cookies for a platform, returns empty dict if none exist."""
    path = get_cookie_file_path(platform)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("cookies", {})
    except Exception:
        pass
    return {}


def has_platform_cookies(platform: str) -> bool:
    """Check if valid cookies are saved for a platform."""
    cookies = load_platform_cookies(platform)
    return bool(cookies)


def list_saved_cookie_platforms() -> List[str]:
    """List all platforms that currently have saved cookies."""
    cdir = get_cookies_dir()
    results: List[str] = []
    for file in cdir.glob("*.json"):
        results.append(file.stem)
    return sorted(results)
