"""Safe-by-default backend dependency installer."""

from __future__ import annotations

import subprocess
import sys
from typing import Dict, List, Optional, Tuple
from neteyes.doctor import is_in_virtualenv

CHANNEL_DEPENDENCIES: Dict[str, List[str]] = {
    "web": ["trafilatura", "beautifulsoup4"],
    "youtube": ["youtube-transcript-api", "yt-dlp"],
    "search": ["duckduckgo-search"],
    "rss": ["feedparser"],
    "reddit": ["praw"],
    "all": [
        "trafilatura",
        "beautifulsoup4",
        "youtube-transcript-api",
        "yt-dlp",
        "duckduckgo-search",
        "feedparser",
        "praw",
    ],
}


def get_missing_packages(packages: List[str]) -> List[str]:
    """Check which packages from the list are not currently installed."""
    missing = []
    for pkg in packages:
        # Normalize package import name vs pip name
        import_name = pkg.replace("-", "_")
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    return missing


def install_packages(
    target: str = "all",
    env: str = "auto",
    check_only: bool = False,
    allow_system: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Install required packages with safety checks.

    Args:
        target: Channel name ('web', 'youtube', 'all') or package name
        env: 'auto', 'venv', or 'system'
        check_only: If True, inspect only without making changes
        allow_system: Explicit permission required to modify system Python

    Returns:
        Tuple of (success: bool, message: str, missing_packages: List[str])
    """
    target_key = target.lower().strip()
    packages_to_check = CHANNEL_DEPENDENCIES.get(target_key, [target])
    missing = get_missing_packages(packages_to_check)

    if not missing:
        return True, f"All dependencies for '{target}' are already installed and healthy.", []

    if check_only:
        return True, f"Missing dependencies for '{target}': {', '.join(missing)} (Check-only mode)", missing

    in_venv = is_in_virtualenv()

    # Safety Guard: Installing into system python requires explicit flag
    if not allow_system and env in ("auto", "system") and not in_venv:
        return (
            True,
            f"Check-only mode (env=auto, no system modifications made).\n"
            f"Missing dependencies for '{target}': {', '.join(missing)}\n"
            f"To install with explicit approval, run:\n"
            f"  neteyes install {target} --env=auto --system",
            missing,
        )

    # Perform installation
    cmd = [sys.executable, "-m", "pip", "install"] + missing
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return True, f"Successfully installed: {', '.join(missing)}", []
        else:
            return False, f"pip installation failed: {proc.stderr.strip()}", missing
    except Exception as e:
        return False, f"Failed to execute pip: {str(e)}", missing
