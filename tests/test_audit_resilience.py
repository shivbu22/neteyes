"""Resilience, fallback, edge-case, and comprehensive audit test suite for NetEyes."""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from neteyes.cli import cli
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.router import route, run, get_ordered_backends
from neteyes.auth import import_cookies_from_text, get_platform_auth_status, delete_platform_cookies
from neteyes.config import set_backend_preference, get_config, reset_config


def test_multi_backend_fallback_cascade():
    """Verify router cascades through fallback backends when primary fails."""
    # Test on web channel where we mock primary trafilatura failure
    with patch("neteyes.backends.web.trafilatura_backend.TrafilaturaBackend.execute") as mock_traf:
        mock_traf.return_value = ExecutionResult(
            success=False,
            channel_id="web",
            action="extract",
            backend_id="trafilatura",
            error="Simulated upstream network timeout (504)",
        )
        
        # When running with fallbacks, it should attempt trafilatura, fail, and succeed via jina or readability
        res = run("web", "extract", url="https://example.com")
        assert "trafilatura" in res.fallbacks_attempted
        # Either succeeded on secondary or gracefully reported all attempts
        if res.success:
            assert res.backend_id != "trafilatura"
            assert len(res.fallbacks_attempted) >= 2


def test_all_backends_failed_graceful_response():
    """Verify clean, structured error when all backends in a channel fail."""
    with patch("neteyes.backends.web.trafilatura_backend.TrafilaturaBackend.execute") as m1, \
         patch("neteyes.backends.web.jina_backend.JinaReaderBackend.execute") as m2, \
         patch("neteyes.backends.web.readability_backend.DirectReadabilityBackend.execute") as m3:
        m1.return_value = ExecutionResult(success=False, channel_id="web", action="extract", backend_id="trafilatura", error="Err 1")
        m2.return_value = ExecutionResult(success=False, channel_id="web", action="extract", backend_id="jina_reader", error="Err 2")
        m3.return_value = ExecutionResult(success=False, channel_id="web", action="extract", backend_id="direct_http", error="Err 3")

        res = run("web", "extract", url="https://example.com")
        assert res.success is False
        assert "All backends failed" in res.error
        assert len(res.fallbacks_attempted) >= 3


def test_missing_required_arguments_handled_gracefully():
    """Verify backends return structured ExecutionResult on missing parameters rather than crashing."""
    # Web without url
    res_web = run("web", "extract")
    assert res_web.success is False
    assert "url" in res_web.error.lower()

    # Search without query
    res_search = run("search", "query")
    assert res_search.success is False
    assert "query" in res_search.error.lower()

    # YouTube without url
    res_yt = run("youtube", "extract")
    assert res_yt.success is False
    assert "url" in res_yt.error.lower()


def test_route_generates_valid_direct_commands_all_channels():
    """Verify route returns valid direct shell commands for core channels."""
    channels_and_args = [
        ("web", "extract", {"url": "https://example.com"}),
        ("youtube", "transcript", {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}),
        ("github", "repo", {"repo": "cli/cli"}),
        ("rss", "read", {"url": "https://news.ycombinator.com/rss"}),
        ("search", "query", {"query": "python releases"}),
        ("reddit", "read_post", {"url": "https://reddit.com/r/python/comments/123"}),
        ("twitter", "read_tweet", {"id": "123456789"}),
        ("bilibili", "video_detail", {"bvid": "BV1xx411c7mD"}),
    ]

    for ch, action, kwargs in channels_and_args:
        decision = route(ch, action, **kwargs)
        assert decision.channel_id == ch
        assert decision.action == action
        assert decision.selected_backend is not None
        assert len(decision.ordered_backends) >= 1
        # Direct command should be generated if supported by active backend
        if decision.direct_command:
            assert isinstance(decision.direct_command, str)
            assert len(decision.direct_command) > 0


def test_cookie_import_malformed_and_valid():
    """Verify robust cookie parsing for valid and corrupted payloads."""
    # Corrupted content raises ValueError
    corrupted_data = "THIS IS NOT JSON OR NETSCAPE COOKIES !@#$%"
    try:
        import_cookies_from_text("twitter", corrupted_data)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    # Valid Cookie-Editor JSON format
    valid_json = json.dumps([
        {"name": "auth_token", "value": "test_token_123", "domain": ".x.com", "path": "/"},
        {"name": "ct0", "value": "test_ct0_456", "domain": ".x.com", "path": "/"},
    ])
    res = import_cookies_from_text("twitter", valid_json)
    assert res["cookie_count"] == 2

    # Verify status
    auth_status = get_platform_auth_status("twitter")
    assert auth_status["has_cookies"] is True
    assert auth_status["cookie_count"] == 2

    # Clear cookies
    delete_platform_cookies("twitter")
    auth_status_after = get_platform_auth_status("twitter")
    assert auth_status_after["has_cookies"] is False


def test_config_backend_preference():
    """Verify overriding backend preferences in config changes ordered backends."""
    backends_before = [b.id for b in get_ordered_backends("web")]
    assert backends_before[0] == "trafilatura"

    # Set jina_reader as preferred
    set_backend_preference("web", "jina_reader")
    backends_after = [b.id for b in get_ordered_backends("web")]
    assert backends_after[0] == "jina_reader"

    # Reset config back to default
    reset_config()
    backends_reset = [b.id for b in get_ordered_backends("web")]
    assert backends_reset[0] == "trafilatura"


def test_cli_full_workflow():
    """Verify complete suite of CLI commands execute cleanly."""
    runner = CliRunner()

    # Help and version
    res = runner.invoke(cli, ["--version"])
    assert res.exit_code == 0
    assert "NetEyes" in res.output

    # List channels
    res = runner.invoke(cli, ["list"])
    assert res.exit_code == 0
    assert "web" in res.output
    assert "youtube" in res.output

    # Doctor JSON output schema
    res = runner.invoke(cli, ["doctor", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert "healthy_channels" in data
    assert "diagnostics" in data
    assert any(d["name"] == "web" for d in data["diagnostics"])

    # Safe install check-only
    res = runner.invoke(cli, ["install", "--env=auto"])
    assert res.exit_code == 0
    assert "Check-only mode" in res.output

    # Route command
    res = runner.invoke(cli, ["route", "web", "extract", "url=https://example.com"])
    assert res.exit_code == 0
    assert "Capability Route:" in res.output
    assert "Selected Backend:" in res.output
