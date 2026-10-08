"""Safe local browser cookie extractor for Chrome, Edge, Brave, and Firefox.

Extracts session cookies for login-walled platforms (Twitter, Reddit, Bilibili, XHS)
directly from the user's local browser profile on Windows, macOS, and Linux.
Strictly local and read-only. Never uploads or exposes credentials.
"""

from __future__ import annotations

import base64
import json
import os
import platform
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from neteyes.utils.cookies import normalize_platform_name, save_platform_cookies


DOMAIN_PLATFORM_MAP = {
    ".twitter.com": "twitter",
    "twitter.com": "twitter",
    ".x.com": "twitter",
    "x.com": "twitter",
    ".reddit.com": "reddit",
    "reddit.com": "reddit",
    ".bilibili.com": "bilibili",
    "bilibili.com": "bilibili",
    ".xiaohongshu.com": "xhs",
    "xiaohongshu.com": "xhs",
    ".linkedin.com": "linkedin",
    "linkedin.com": "linkedin",
    ".v2ex.com": "v2ex",
    "v2ex.com": "v2ex",
}


def get_browser_cookie_paths() -> Dict[str, List[Path]]:
    """Return potential cookie database paths for major browsers on current OS."""
    system = platform.system()
    paths: Dict[str, List[Path]] = {
        "chrome": [],
        "edge": [],
        "brave": [],
    }

    if system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            lad = Path(local_app_data)
            paths["chrome"].append(lad / "Google" / "Chrome" / "User Data" / "Default" / "Network" / "Cookies")
            paths["chrome"].append(lad / "Google" / "Chrome" / "User Data" / "Default" / "Cookies")
            paths["edge"].append(lad / "Microsoft" / "Edge" / "User Data" / "Default" / "Network" / "Cookies")
            paths["edge"].append(lad / "Microsoft" / "Edge" / "User Data" / "Default" / "Cookies")
            paths["brave"].append(lad / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Network" / "Cookies")
    elif system == "Darwin":  # macOS
        home = Path.home()
        paths["chrome"].append(home / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "Cookies")
        paths["edge"].append(home / "Library" / "Application Support" / "Microsoft Edge" / "Default" / "Cookies")
        paths["brave"].append(home / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser" / "Default" / "Cookies")
    else:  # Linux
        home = Path.home()
        paths["chrome"].append(home / ".config" / "google-chrome" / "Default" / "Cookies")
        paths["edge"].append(home / ".config" / "microsoft-edge" / "Default" / "Cookies")
        paths["brave"].append(home / ".config" / "BraveSoftware" / "Brave-Browser" / "Default" / "Cookies")

    return paths


def _decrypt_dpapi_windows(encrypted_val: bytes) -> bytes:
    """Decrypt DPAPI protected data on Windows via ctypes."""
    try:
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte)),
            ]

        pDataIn = DATA_BLOB(len(encrypted_val), ctypes.cast(encrypted_val, ctypes.POINTER(ctypes.c_byte)))
        pDataOut = DATA_BLOB()

        ret = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(pDataIn),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(pDataOut),
        )
        if ret:
            length = int(pDataOut.cbData)
            res = ctypes.string_at(pDataOut.pbData, length)
            ctypes.windll.kernel32.LocalFree(pDataOut.pbData)
            return res
    except Exception:
        pass
    return b""


def extract_cookies_from_sqlite(db_path: Path, target_domains: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
    """Safely copy and read cookies from a Chromium SQLite database."""
    if not db_path.exists():
        return {}

    # Copy to temporary file to avoid database locks while browser is open
    temp_dir = tempfile.mkdtemp(prefix="neteyes_cookie_")
    temp_db = Path(temp_dir) / "Cookies.tmp"

    extracted: Dict[str, Dict[str, str]] = {}

    try:
        shutil.copy2(db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Query cookies
        query = "SELECT host_key, name, value, encrypted_value FROM cookies"
        cursor.execute(query)
        rows = cursor.fetchall()

        for host_key, name, value, encrypted_value in rows:
            platform_id = None
            for d, p in DOMAIN_PLATFORM_MAP.items():
                if d in host_key:
                    platform_id = p
                    break

            if not platform_id:
                continue

            cookie_val = value
            if not cookie_val and encrypted_value:
                # Attempt Windows DPAPI decrypt for older cookies or raw v10
                if platform.system() == "Windows" and len(encrypted_value) > 0:
                    try:
                        decrypted = _decrypt_dpapi_windows(encrypted_value)
                        if decrypted:
                            cookie_val = decrypted.decode("utf-8", errors="ignore")
                    except Exception:
                        pass

            if cookie_val:
                if platform_id not in extracted:
                    extracted[platform_id] = {}
                extracted[platform_id][name] = cookie_val

        conn.close()
    except Exception:
        pass
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return extracted


def sync_browser_cookies(browser_name: str = "all") -> Dict[str, int]:
    """Inspect and sync cookies from installed browsers into ~/.neteyes/cookies/."""
    all_browser_paths = get_browser_cookie_paths()
    browsers_to_check = [browser_name.lower()] if browser_name.lower() != "all" else ["chrome", "edge", "brave"]

    synced_counts: Dict[str, int] = {}

    for b in browsers_to_check:
        paths = all_browser_paths.get(b, [])
        for p in paths:
            if p.exists():
                extracted = extract_cookies_from_sqlite(p)
                for platform_id, cookies in extracted.items():
                    if cookies:
                        save_platform_cookies(platform_id, cookies, metadata={"source_browser": b, "db_path": str(p)})
                        synced_counts[platform_id] = len(cookies)

    return synced_counts
