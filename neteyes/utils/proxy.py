"""Proxy pool and anti-blocking rotation manager for NetEyes.

Manages HTTP, HTTPS, and SOCKS5 proxy pools, health probes,
automatic rotation (round-robin, random, failover), and persistence.
"""

from __future__ import annotations

import json
import random
import time
from typing import Any, Dict, List, Optional
import httpx

from neteyes.config import get_cache_dir, load_config, save_config


VALID_STRATEGIES = ["round_robin", "random", "failover"]


def _get_proxy_state_file():
    return get_cache_dir() / "proxy_state.json"


def _load_proxy_state() -> Dict[str, Any]:
    p = _get_proxy_state_file()
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_index": 0, "failed_proxies": {}}


def _save_proxy_state(state: Dict[str, Any]) -> None:
    p = _get_proxy_state_file()
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def list_proxies() -> List[str]:
    """Return all configured proxies in priority order."""
    cfg = load_config()
    proxies = cfg.get("proxies") or []
    single_proxy = cfg.get("proxy")
    
    # If legacy single proxy is set but not in list, add it
    if single_proxy and single_proxy not in proxies:
        proxies.insert(0, single_proxy)
    return proxies


def add_proxy(proxy_url: str) -> bool:
    """Add a proxy to the pool (deduplicated)."""
    proxy_url = proxy_url.strip()
    if not proxy_url.startswith(("http://", "https://", "socks5://", "socks5h://")):
        raise ValueError(f"Invalid proxy schema: '{proxy_url}'. Must begin with http://, https://, or socks5://")

    cfg = load_config()
    proxies: List[str] = cfg.get("proxies") or []
    if proxy_url not in proxies:
        proxies.append(proxy_url)
        cfg["proxies"] = proxies
        # If no active single proxy, set this as primary
        if not cfg.get("proxy"):
            cfg["proxy"] = proxy_url
        save_config(cfg)
        return True
    return False


def remove_proxy(proxy_url: str) -> bool:
    """Remove a proxy from the pool."""
    proxy_url = proxy_url.strip()
    cfg = load_config()
    proxies: List[str] = cfg.get("proxies") or []
    if proxy_url in proxies:
        proxies.remove(proxy_url)
        cfg["proxies"] = proxies
        if cfg.get("proxy") == proxy_url:
            cfg["proxy"] = proxies[0] if proxies else None
        save_config(cfg)
        return True
    return False


def clear_proxies() -> int:
    """Clear all proxies from the pool."""
    cfg = load_config()
    count = len(cfg.get("proxies") or [])
    cfg["proxies"] = []
    cfg["proxy"] = None
    save_config(cfg)
    _save_proxy_state({"current_index": 0, "failed_proxies": {}})
    return count


def set_proxy_strategy(strategy: str) -> None:
    """Set proxy selection strategy ('round_robin', 'random', 'failover')."""
    strat = strategy.lower().strip()
    if strat not in VALID_STRATEGIES:
        raise ValueError(f"Unknown proxy strategy '{strategy}'. Valid options: {', '.join(VALID_STRATEGIES)}")
    cfg = load_config()
    cfg["proxy_strategy"] = strat
    save_config(cfg)


def get_proxy_strategy() -> str:
    """Get active proxy rotation strategy."""
    cfg = load_config()
    return cfg.get("proxy_strategy", "round_robin")


def get_next_proxy(rotate: bool = True) -> Optional[str]:
    """Retrieve next proxy URL based on configured rotation strategy."""
    proxies = list_proxies()
    if not proxies:
        return None

    strategy = get_proxy_strategy()
    state = _load_proxy_state()
    current_idx = state.get("current_index", 0)

    if strategy == "random":
        chosen = random.choice(proxies)
        return chosen

    if strategy == "failover":
        # Always pick the first healthy proxy
        failed = state.get("failed_proxies", {})
        now = time.time()
        for p in proxies:
            fail_time = failed.get(p, 0)
            # If fail was more than 5 minutes ago, allow retry
            if now - fail_time > 300:
                return p
        # If all failed, return first as fallback
        return proxies[0]

    # Default: round_robin
    if current_idx >= len(proxies):
        current_idx = 0
    selected = proxies[current_idx]

    if rotate:
        state["current_index"] = (current_idx + 1) % len(proxies)
        _save_proxy_state(state)

    return selected


def mark_proxy_failed(proxy_url: str) -> None:
    """Mark a proxy as failed to temporarily bypass it in failover mode."""
    state = _load_proxy_state()
    failed = state.get("failed_proxies", {})
    failed[proxy_url] = time.time()
    state["failed_proxies"] = failed
    _save_proxy_state(state)


def probe_proxy(proxy_url: str, probe_url: str = "https://httpbin.org/ip", timeout: float = 5.0) -> Dict[str, Any]:
    """Test proxy reachability and measure round-trip latency."""
    t0 = time.time()
    try:
        with httpx.Client(proxy=proxy_url, timeout=timeout, verify=True) as client:
            resp = client.get(probe_url)
            elapsed_ms = round((time.time() - t0) * 1000, 1)
            if resp.status_code == 200:
                ip = ""
                try:
                    ip = resp.json().get("origin", "")
                except Exception:
                    pass
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "latency_ms": elapsed_ms,
                    "ip": ip,
                    "proxy": proxy_url,
                }
            return {
                "success": False,
                "status_code": resp.status_code,
                "latency_ms": elapsed_ms,
                "error": f"HTTP {resp.status_code}",
                "proxy": proxy_url,
            }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        mark_proxy_failed(proxy_url)
        return {
            "success": False,
            "status_code": None,
            "latency_ms": elapsed_ms,
            "error": str(e),
            "proxy": proxy_url,
        }


test_proxy = probe_proxy
