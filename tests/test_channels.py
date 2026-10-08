"""Tests for channel specifications and registry."""

from neteyes.channels import (
    CHANNEL_REGISTRY,
    get_backends_for_channel,
    get_channel,
    list_channels,
    normalize_channel_id,
)


def test_channel_registry_completeness():
    """Verify all expected core platforms are present in the registry."""
    expected = [
        "web",
        "youtube",
        "twitter",
        "reddit",
        "github",
        "bilibili",
        "xhs",
        "rss",
        "search",
    ]
    for ch_id in expected:
        assert ch_id in CHANNEL_REGISTRY
        channel = get_channel(ch_id)
        assert channel is not None
        spec = channel.get_spec()
        assert spec.id == ch_id
        assert len(spec.actions) > 0
        assert len(spec.backends) > 0


def test_channel_alias_normalization():
    """Verify aliases resolve to correct channel IDs."""
    assert normalize_channel_id("x") == "twitter"
    assert normalize_channel_id("yt") == "youtube"
    assert normalize_channel_id("gh") == "github"
    assert normalize_channel_id("bili") == "bilibili"
    assert normalize_channel_id("redbook") == "xhs"
    assert normalize_channel_id("ddg") == "search"
    assert normalize_channel_id("feed") == "rss"


def test_channel_backends_ordering():
    """Verify channels have backends ordered by priority."""
    channels = list_channels()
    assert len(channels) >= 9

    for ch_spec in channels:
        backends = get_backends_for_channel(ch_spec.id)
        assert len(backends) > 0
        priorities = [b.priority for b in backends]
        assert priorities == sorted(priorities), f"Channel {ch_spec.id} backends not sorted by priority"
