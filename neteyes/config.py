"""Configuration management for NetEyes."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def get_neteyes_home() -> Path:
    """Return the base directory for NetEyes configuration and cookies."""
    override = os.environ.get("NETEYES_HOME")
    if override:
        path = Path(override).expanduser().resolve()
    else:
        path = Path.home() / ".neteyes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cookies_dir() -> Path:
    """Return directory where session cookies are stored."""
    cdir = get_neteyes_home() / "cookies"
    cdir.mkdir(parents=True, exist_ok=True)
    return cdir


def get_cache_dir() -> Path:
    """Return directory for temporary cache."""
    cdir = get_neteyes_home() / "cache"
    cdir.mkdir(parents=True, exist_ok=True)
    return cdir


def get_config_file() -> Path:
    """Return path to user configuration file."""
    return get_neteyes_home() / "config.json"


DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "0.1.0",
    "timeout_seconds": 15,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (NetEyes/0.1.0)",
    "preferred_backends": {},  # channel_id -> backend_id
    "disabled_backends": [],
    "proxy": None,
    "output_format": "markdown",
}


def load_config() -> Dict[str, Any]:
    """Load user configuration from disk or create default."""
    cfg_file = get_config_file()
    if not cfg_file.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            return merged
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(config_data: Dict[str, Any]) -> None:
    """Persist user configuration to disk."""
    cfg_file = get_config_file()
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)


def get_preferred_backend(channel_id: str) -> Optional[str]:
    """Get preferred backend override if configured."""
    cfg = load_config()
    return cfg.get("preferred_backends", {}).get(channel_id)


def set_preferred_backend(channel_id: str, backend_id: str) -> None:
    """Set preferred backend override for a channel."""
    cfg = load_config()
    if "preferred_backends" not in cfg:
        cfg["preferred_backends"] = {}
    cfg["preferred_backends"][channel_id] = backend_id
    save_config(cfg)
