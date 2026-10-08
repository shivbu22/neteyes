"""Authentication and browser cookie session manager.

Designed for AI agent workflows:
Supports Cookie-Editor browser extension JSON exports, Netscape cookies.txt,
and Cookie HTTP headers for walled platforms (Twitter/X, Bilibili, Xiaohongshu, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from neteyes.models import HealthStatus
from neteyes.utils.cookies import (
    get_cookie_file_path,
    has_platform_cookies,
    list_saved_cookie_platforms,
    load_platform_cookies,
    normalize_platform_name,
    parse_cookie_input,
    save_platform_cookies,
)

# Known critical session cookie names per platform
PLATFORM_COOKIE_SIGNATURES: Dict[str, List[str]] = {
    "twitter": ["auth_token", "ct0"],
    "bilibili": ["SESSDATA", "bili_jct"],
    "xhs": ["a1", "web_session"],
    "reddit": ["reddit_session"],
    "linkedin": ["li_at"],
    "instagram": ["sessionid"],
    "facebook": ["c_user", "xs"],
    "v2ex": ["PB3_SESSION"],
    "xueqiu": ["xq_a_token"],
    "boss": ["wt2"],
}


def import_cookies_from_file(platform: str, file_path: str | Path) -> Dict[str, Any]:
    """Import cookies from a Cookie-Editor JSON or cookies.txt file."""
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Cookie file not found: {path}")

    content = path.read_text(encoding="utf-8", errors="ignore")
    cookies = parse_cookie_input(content)
    if not cookies:
        raise ValueError(f"Could not parse any valid cookies from file: {path}")

    norm_platform = normalize_platform_name(platform)
    saved_path = save_platform_cookies(
        norm_platform,
        cookies,
        metadata={"source_file": str(path)}
    )
    return {
        "platform": norm_platform,
        "cookie_count": len(cookies),
        "saved_path": str(saved_path),
        "keys": list(cookies.keys()),
    }


def import_cookies_from_text(platform: str, raw_text: str) -> Dict[str, Any]:
    """Import cookies directly from pasted text (JSON or header string)."""
    cookies = parse_cookie_input(raw_text)
    if not cookies:
        raise ValueError("Could not parse any cookies from provided text")

    norm_platform = normalize_platform_name(platform)
    saved_path = save_platform_cookies(
        norm_platform,
        cookies,
        metadata={"source": "pasted_text"}
    )
    return {
        "platform": norm_platform,
        "cookie_count": len(cookies),
        "saved_path": str(saved_path),
        "keys": list(cookies.keys()),
    }


def get_platform_auth_status(platform: str) -> Dict[str, Any]:
    """Check authentication status and presence of key tokens for a platform."""
    norm = normalize_platform_name(platform)
    cookies = load_platform_cookies(norm)
    if not cookies:
        return {
            "platform": norm,
            "status": HealthStatus.REQUIRES_AUTH,
            "has_cookies": False,
            "cookie_count": 0,
            "missing_keys": PLATFORM_COOKIE_SIGNATURES.get(norm, []),
            "message": "No cookies stored. Import cookies via 'neteyes auth <platform> --import <file>'",
        }

    signatures = PLATFORM_COOKIE_SIGNATURES.get(norm, [])
    present_sigs = [k for k in signatures if k in cookies]
    missing_sigs = [k for k in signatures if k not in cookies]

    if signatures and missing_sigs:
        return {
            "platform": norm,
            "status": HealthStatus.DEGRADED,
            "has_cookies": True,
            "cookie_count": len(cookies),
            "present_keys": present_sigs,
            "missing_keys": missing_sigs,
            "message": f"Cookies present ({len(cookies)}), but missing critical keys: {', '.join(missing_sigs)}",
        }

    return {
        "platform": norm,
        "status": HealthStatus.HEALTHY,
        "has_cookies": True,
        "cookie_count": len(cookies),
        "present_keys": present_sigs,
        "message": f"Active session with {len(cookies)} cookies stored",
    }


def delete_platform_cookies(platform: str) -> bool:
    """Delete stored cookies for a platform."""
    path = get_cookie_file_path(platform)
    if path.exists():
        path.unlink()
        return True
    return False


def get_all_auth_statuses() -> List[Dict[str, Any]]:
    """Return auth status for all known login-walled platforms."""
    results: List[Dict[str, Any]] = []
    for platform in PLATFORM_COOKIE_SIGNATURES:
        results.append(get_platform_auth_status(platform))
    return results
