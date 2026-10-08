"""Tests for Click CLI entrypoint."""

import json
from click.testing import CliRunner
from neteyes.cli import cli


def test_cli_version():
    """Verify CLI --version returns NetEyes version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "NetEyes v" in result.output


def test_cli_help():
    """Verify CLI --help shows all core subcommands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.output
    assert "route" in result.output
    assert "run" in result.output
    assert "install" in result.output
    assert "list" in result.output
    assert "auth" in result.output
    assert "config" in result.output


def test_cli_list():
    """Verify neteyes list renders channels table."""
    runner = CliRunner()
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "web" in result.output
    assert "youtube" in result.output
    assert "reddit" in result.output


def test_cli_route():
    """Verify neteyes route outputs selected backend and command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["route", "web", "extract", "https://example.com"])
    assert result.exit_code == 0
    assert "Selected Backend" in result.output
    assert "Direct Upstream Command" in result.output


def test_cli_doctor_json():
    """Verify neteyes doctor --json outputs parseable JSON."""
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "healthy_channels" in data
    assert "diagnostics" in data


def test_cli_auth_status():
    """Verify neteyes auth status lists platform statuses."""
    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "status"])
    assert result.exit_code == 0
    assert "twitter" in result.output.lower()
