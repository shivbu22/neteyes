"""Tests for capability routing and execution engine."""

from neteyes.models import HealthStatus
from neteyes.router import get_ordered_backends, route, run


def test_route_web():
    """Verify routing web extraction returns Trafilatura or Jina and direct command."""
    decision = route("web", "extract", url="https://example.com")
    assert decision.channel_id == "web"
    assert decision.action == "extract"
    assert decision.selected_backend is not None
    assert decision.direct_command is not None
    assert "example.com" in decision.direct_command
    assert len(decision.ordered_backends) >= 3


def test_route_youtube():
    """Verify routing youtube transcript generation."""
    decision = route("youtube", "transcript", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert decision.channel_id == "youtube"
    assert decision.action == "transcript"
    assert "youtube" in decision.selected_backend.id


def test_route_unknown_channel():
    """Verify routing invalid channel raises ValueError."""
    try:
        route("non_existent_channel", "action")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown channel" in str(e)


def test_run_unknown_channel():
    """Verify run on invalid channel gracefully fails."""
    res = run("invalid_platform", "action")
    assert res.success is False
    assert "Unknown channel" in res.error
