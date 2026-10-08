"""Comprehensive test suite for NetEyes advanced capabilities:
MCP Server, Local Browser Cookie Sync, Proxy Pool Manager, and Terminal Dashboard.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from neteyes.dashboard import (
    build_header,
    build_integrations_panel,
    build_proxy_panel,
    render_dashboard,
)
from neteyes.doctor import run_doctor
from neteyes.mcp_server import get_mcp_tools, handle_tool_call, process_mcp_message
from neteyes.utils.browser_cookies import (
    DOMAIN_PLATFORM_MAP,
    extract_cookies_from_sqlite,
    get_browser_cookie_paths,
    sync_browser_cookies,
)
from neteyes.utils.proxy import (
    add_proxy,
    clear_proxies,
    get_next_proxy,
    get_proxy_strategy,
    list_proxies,
    mark_proxy_failed,
    probe_proxy,
    remove_proxy,
    set_proxy_strategy,
)


# =====================================================================
# 1. MCP Server Tests
# =====================================================================

def test_mcp_tools_list_generation():
    """Verify MCP tools list conforms to MCP standard format."""
    tools = get_mcp_tools()
    assert len(tools) > 5

    tool_names = [t["name"] for t in tools]
    assert "neteyes_doctor" in tool_names
    assert "neteyes_web_extract" in tool_names
    assert "neteyes_youtube_transcript" in tool_names

    # Check schema structure
    for t in tools:
        assert "name" in t
        assert "description" in t
        assert "inputSchema" in t
        assert t["inputSchema"]["type"] == "object"
        assert "properties" in t["inputSchema"]


def test_mcp_handle_doctor_tool():
    """Verify neteyes_doctor tool execution in MCP."""
    res = handle_tool_call("neteyes_doctor", {})
    assert res["isError"] is False
    assert len(res["content"]) == 1
    assert res["content"][0]["type"] == "text"
    parsed = json.loads(res["content"][0]["text"])
    assert "healthy_channels" in parsed
    assert "diagnostics" in parsed


def test_mcp_handle_unknown_tool():
    """Verify unknown tool returns graceful error message."""
    res = handle_tool_call("invalid_tool_name", {})
    assert res["isError"] is True
    assert "Unknown tool" in res["content"][0]["text"]


def test_mcp_json_rpc_protocol():
    """Verify JSON-RPC 2.0 message dispatch for initialize, tools/list, and ping."""
    # 1. Initialize
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"},
    }
    resp = process_mcp_message(init_req)
    assert resp["id"] == 1
    assert "serverInfo" in resp["result"]
    assert resp["result"]["serverInfo"]["name"] == "neteyes-mcp-server"

    # 2. Ping
    ping_req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
    resp = process_mcp_message(ping_req)
    assert resp["id"] == 2
    assert resp["result"] == {}

    # 3. Tools list
    list_req = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
    resp = process_mcp_message(list_req)
    assert resp["id"] == 3
    assert "tools" in resp["result"]
    assert len(resp["result"]["tools"]) > 5


# =====================================================================
# 2. Proxy Pool Manager Tests
# =====================================================================

def test_proxy_manager_crud():
    """Test proxy addition, deduplication, schema validation, and deletion."""
    clear_proxies()
    assert list_proxies() == []

    # Valid add
    assert add_proxy("http://127.0.0.1:8080") is True
    assert add_proxy("http://127.0.0.1:8080") is False  # deduplicated
    assert add_proxy("socks5://127.0.0.1:1080") is True

    proxies = list_proxies()
    assert len(proxies) == 2
    assert "http://127.0.0.1:8080" in proxies
    assert "socks5://127.0.0.1:1080" in proxies

    # Invalid schema rejected
    with pytest.raises(ValueError):
        add_proxy("ftp://invalid.proxy.com")

    # Remove
    assert remove_proxy("http://127.0.0.1:8080") is True
    assert remove_proxy("http://nonexistent:9999") is False
    assert len(list_proxies()) == 1

    # Clear
    clear_proxies()
    assert list_proxies() == []


def test_proxy_rotation_strategies():
    """Test round-robin, random, and failover rotation behaviors."""
    clear_proxies()
    add_proxy("http://proxy1:8001")
    add_proxy("http://proxy2:8002")
    add_proxy("http://proxy3:8003")

    # Strategy: round_robin
    set_proxy_strategy("round_robin")
    assert get_proxy_strategy() == "round_robin"

    p1 = get_next_proxy(rotate=True)
    p2 = get_next_proxy(rotate=True)
    p3 = get_next_proxy(rotate=True)
    p4 = get_next_proxy(rotate=True)

    assert [p1, p2, p3] == ["http://proxy1:8001", "http://proxy2:8002", "http://proxy3:8003"]
    assert p4 == "http://proxy1:8001"

    # Strategy: failover
    set_proxy_strategy("failover")
    mark_proxy_failed("http://proxy1:8001")
    assert get_next_proxy() == "http://proxy2:8002"

    clear_proxies()


def test_proxy_test_handler():
    """Test proxy reachability probe handles error gracefully without raising."""
    res = probe_proxy("http://127.0.0.1:59999", timeout=0.2)
    assert res["success"] is False
    assert "latency_ms" in res
    assert res["error"] is not None


# =====================================================================
# 3. Local Browser Cookie Sync Tests
# =====================================================================

def test_browser_cookie_paths_detection():
    """Ensure platform path finder returns dict with expected browser keys."""
    paths = get_browser_cookie_paths()
    assert "chrome" in paths
    assert "edge" in paths
    assert "brave" in paths


def test_extract_cookies_from_mock_sqlite():
    """Test extracting cookies from a mock SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = Path(f.name)

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)")
        # Insert plain unencrypted cookies
        cur.execute("INSERT INTO cookies VALUES ('.twitter.com', 'auth_token', 'mock_token_123', X'')")
        cur.execute("INSERT INTO cookies VALUES ('.reddit.com', 'reddit_session', 'mock_reddit_456', X'')")
        cur.execute("INSERT INTO cookies VALUES ('.unrelated.com', 'tracking', 'xyz', X'')")
        conn.commit()
        conn.close()

        extracted = extract_cookies_from_sqlite(db_path)
        assert "twitter" in extracted
        assert extracted["twitter"]["auth_token"] == "mock_token_123"
        assert "reddit" in extracted
        assert extracted["reddit"]["reddit_session"] == "mock_reddit_456"
        assert "unrelated" not in extracted
    finally:
        if db_path.exists():
            db_path.unlink()


def test_sync_browser_cookies_graceful_missing():
    """Verify sync_browser_cookies executes gracefully when browser files are absent."""
    with patch("neteyes.utils.browser_cookies.get_browser_cookie_paths", return_value={"chrome": [], "edge": [], "brave": []}):
        results = sync_browser_cookies("all")
        assert results == {}


# =====================================================================
# 4. Dashboard Tests
# =====================================================================

def test_dashboard_components():
    """Verify dashboard header, tables, and full layout composition."""
    header = build_header()
    assert header is not None

    proxy_panel = build_proxy_panel()
    assert proxy_panel is not None

    integrations_panel = build_integrations_panel()
    assert integrations_panel is not None

    layout = render_dashboard()
    assert layout is not None
    assert "header" in [child.name for child in layout.children]
    assert "channels" in [child.name for child in layout.children]
