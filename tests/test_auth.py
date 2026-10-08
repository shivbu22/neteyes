"""Tests for cookie parsing and session authentication."""

import json
from pathlib import Path
from neteyes.auth import (
    delete_platform_cookies,
    get_platform_auth_status,
    import_cookies_from_file,
    import_cookies_from_text,
)
from neteyes.models import HealthStatus
from neteyes.utils.cookies import (
    parse_cookie_editor_json,
    parse_cookie_input,
    parse_netscape_cookies,
)


def test_parse_cookie_editor_json():
    """Verify Cookie-Editor array export is parsed correctly."""
    sample_json = json.dumps([
        {"name": "auth_token", "value": "secret_token_123", "domain": ".x.com"},
        {"name": "ct0", "value": "csrf_token_456", "domain": ".x.com"},
    ])
    cookies = parse_cookie_editor_json(sample_json)
    assert cookies["auth_token"] == "secret_token_123"
    assert cookies["ct0"] == "csrf_token_456"


def test_parse_netscape_cookies():
    """Verify Netscape cookies.txt format is parsed correctly."""
    sample_netscape = (
        "# Netscape HTTP Cookie File\n"
        ".x.com\tTRUE\t/\tTRUE\t1790000000\tauth_token\tnetscape_token_789\n"
        ".x.com\tTRUE\t/\tTRUE\t1790000000\tct0\tnetscape_csrf_101\n"
    )
    cookies = parse_netscape_cookies(sample_netscape)
    assert cookies["auth_token"] == "netscape_token_789"
    assert cookies["ct0"] == "netscape_csrf_101"


def test_import_and_lifecycle(tmp_path: Path, monkeypatch):
    """Test importing cookies from text and checking status."""
    # Isolate storage directory for test
    test_home = tmp_path / "neteyes_test"
    monkeypatch.setenv("NETEYES_HOME", str(test_home))

    # Initial status should require auth
    status_before = get_platform_auth_status("twitter")
    assert status_before["status"] == HealthStatus.REQUIRES_AUTH

    # Import cookies
    raw = json.dumps([
        {"name": "auth_token", "value": "test_auth"},
        {"name": "ct0", "value": "test_ct0"},
    ])
    result = import_cookies_from_text("twitter", raw)
    assert result["cookie_count"] == 2

    # Status after import should be healthy
    status_after = get_platform_auth_status("twitter")
    assert status_after["status"] == HealthStatus.HEALTHY
    assert status_after["has_cookies"] is True

    # Delete cookies
    assert delete_platform_cookies("twitter") is True
    status_deleted = get_platform_auth_status("twitter")
    assert status_deleted["has_cookies"] is False
