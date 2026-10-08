"""NetEyes CLI Entrypoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import click
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from neteyes import __version__
from neteyes.auth import (
    delete_platform_cookies,
    get_all_auth_statuses,
    get_platform_auth_status,
    import_cookies_from_file,
    import_cookies_from_text,
)
from neteyes.channels import list_channels, normalize_channel_id
from neteyes.config import load_config, save_config, set_preferred_backend
from neteyes.doctor import run_doctor
from neteyes.installer import install_packages
from neteyes.models import HealthStatus
from neteyes.router import route as route_action, run as run_action
from neteyes.utils.console import (
    console,
    err_console,
    print_banner,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show NetEyes version.")
@click.pass_context
def cli(ctx: click.Context, version: bool) -> None:
    """NetEyes: Give any AI agent real eyes on the internet.

    A capability routing and health checking layer for modern AI agents.
    """
    if version:
        console.print(f"NetEyes v{__version__}")
        sys.exit(0)
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print(ctx.get_help())


@cli.command("doctor")
@click.option("--json", "json_output", is_flag=True, help="Output health diagnostic report in JSON.")
def doctor_cmd(json_output: bool) -> None:
    """Run deep health check on backends, binaries, cookies, and dependencies."""
    report = run_doctor()

    if json_output:
        click.echo(report.model_dump_json(indent=2))
        return

    print_banner()
    console.print(f"[bold]System Diagnostic Report[/bold]  ({report.timestamp})")
    console.print(f"OS: {report.os_name} | Python: {report.python_version} (Virtualenv: {report.in_virtualenv})\n")

    # Table of diagnostics
    table = Table(show_header=True, header_style="bold", border_style="dim")
    table.add_column("Category", style="cyan", width=12)
    table.add_column("Component", style="bold", width=18)
    table.add_column("Status", width=14)
    table.add_column("Active Backend", style="green", width=20)
    table.add_column("Details", style="dim")

    for item in report.diagnostics:
        status_style = {
            HealthStatus.HEALTHY: "[green]healthy[/green]",
            HealthStatus.DEGRADED: "[yellow]degraded[/yellow]",
            HealthStatus.REQUIRES_AUTH: "[yellow]requires auth[/yellow]",
            HealthStatus.MISSING_DEPENDENCY: "[red]missing dep[/red]",
            HealthStatus.UNAVAILABLE: "[red]unavailable[/red]",
        }.get(item.status, item.status.value)

        active_col = item.active_backend if item.active_backend else "-"
        table.add_row(item.category, item.name, status_style, active_col, item.message)

    console.print(table)
    console.print()

    # Prescriptions section
    if report.fix_prescriptions:
        prescriptions_text = "\n".join([f"• {p}" for p in report.fix_prescriptions])
        panel = Panel(
            prescriptions_text,
            title="[bold yellow]Recommended Fix Prescriptions[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
        console.print(panel)
    else:
        print_success("All channels and backends are healthy. NetEyes is ready for agent operations.")


@cli.command("route")
@click.argument("channel")
@click.argument("action")
@click.argument("extra_args", nargs=-1)
@click.option("--json", "json_output", is_flag=True, help="Output routing decision as JSON.")
def route_cmd(channel: str, action: str, extra_args: tuple, json_output: bool) -> None:
    """Route an action to the optimal upstream tool and generate direct CLI command."""
    # Parse extra args: first arg is primary parameter or key=value pairs
    kwargs: Dict[str, Any] = {}
    if extra_args:
        first = extra_args[0]
        # Infer primary param based on channel
        cid = normalize_channel_id(channel)
        is_url = first.startswith(("http://", "https://"))
        if is_url or "=" not in first:
            if cid in ("web", "rss", "podcast"):
                kwargs["url"] = first
            elif cid == "youtube":
                if action == "search":
                    kwargs["query"] = " ".join(extra_args)
                else:
                    kwargs["url"] = first
            elif cid == "search":
                kwargs["query"] = " ".join(extra_args)
            elif cid == "github":
                kwargs["repo"] = first
            elif cid == "reddit":
                if action == "search":
                    kwargs["query"] = " ".join(extra_args)
                elif action == "post":
                    kwargs["url"] = first
                else:
                    kwargs["subreddit"] = first
            elif cid == "twitter":
                if action == "user":
                    kwargs["username"] = first
                else:
                    kwargs["url"] = first
            elif cid == "bilibili":
                if action == "search":
                    kwargs["query"] = " ".join(extra_args)
                else:
                    kwargs["bvid"] = first
            elif cid == "xhs":
                kwargs["url"] = first
            else:
                kwargs["query"] = first

        # Parse key=value arguments
        for arg in extra_args:
            if "=" in arg and not arg.startswith(("http://", "https://")):
                k, v = arg.split("=", 1)
                kwargs[k.strip()] = v.strip()

    try:
        decision = route_action(channel, action, **kwargs)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)

    if json_output:
        click.echo(decision.model_dump_json(indent=2))
        return

    print_header(f"Capability Route: {decision.channel_id} -> {decision.action}")
    console.print(f"[bold cyan]Selected Backend:[/bold cyan] {decision.selected_backend.name} (`{decision.selected_backend.id}`)")
    console.print(f"[bold cyan]Routing Reason:[/bold cyan]   {decision.routing_reason}")
    console.print(f"[bold cyan]Fallback Chain:[/bold cyan]   {' -> '.join(decision.ordered_backends)}")

    if decision.direct_command:
        console.print()
        cmd_panel = Panel(
            Syntax(decision.direct_command, "bash", theme="monokai", word_wrap=True),
            title="[bold green]Direct Upstream Command (Run in Shell)[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
        console.print(cmd_panel)
    elif decision.usage_notes:
        console.print(f"\n[dim]{decision.usage_notes}[/dim]")


@cli.command("run")
@click.argument("channel")
@click.argument("action")
@click.argument("extra_args", nargs=-1)
@click.option("--format", "output_format", type=click.Choice(["markdown", "json", "raw"]), default="markdown", help="Output format.")
@click.option("--backend", "backend_override", default=None, help="Force specific backend adapter.")
def run_cmd(channel: str, action: str, extra_args: tuple, output_format: str, backend_override: Optional[str]) -> None:
    """Execute an action through the best healthy backend with auto-fallback."""
    kwargs: Dict[str, Any] = {}
    if extra_args:
        first = extra_args[0]
        cid = normalize_channel_id(channel)
        is_url = first.startswith(("http://", "https://"))
        if is_url or "=" not in first:
            if cid in ("web", "rss", "podcast"):
                kwargs["url"] = first
            elif cid == "youtube":
                if action == "search":
                    kwargs["query"] = " ".join(extra_args)
                else:
                    kwargs["url"] = first
            elif cid == "search":
                kwargs["query"] = " ".join(extra_args)
            elif cid == "github":
                kwargs["repo"] = first
            elif cid == "reddit":
                if action == "search":
                    kwargs["query"] = " ".join(extra_args)
                elif action == "post":
                    kwargs["url"] = first
                else:
                    kwargs["subreddit"] = first
            elif cid == "twitter":
                if action == "user":
                    kwargs["username"] = first
                else:
                    kwargs["url"] = first
            elif cid == "bilibili":
                if action == "search":
                    kwargs["query"] = " ".join(extra_args)
                else:
                    kwargs["bvid"] = first
            elif cid == "xhs":
                kwargs["url"] = first
            else:
                kwargs["query"] = first

        for arg in extra_args:
            if "=" in arg and not arg.startswith(("http://", "https://")):
                k, v = arg.split("=", 1)
                kwargs[k.strip()] = v.strip()

    result = run_action(channel, action, backend_override=backend_override, **kwargs)

    if not result.success:
        print_error(f"Execution failed: {result.error}")
        if result.fallbacks_attempted:
            console.print(f"[dim]Backends attempted: {', '.join(result.fallbacks_attempted)}[/dim]")
        sys.exit(1)

    if output_format == "json":
        click.echo(json.dumps(result.data, indent=2, ensure_ascii=False))
    elif output_format == "raw":
        click.echo(result.raw or str(result.data))
    else:
        # Default: clean markdown
        click.echo(result.markdown or str(result.data))


@cli.command("install")
@click.argument("target", default="all")
@click.option("--env", "env_type", type=click.Choice(["auto", "venv", "system"]), default="auto", help="Installation target environment.")
@click.option("--check-only", is_flag=True, help="Preview missing dependencies without installing.")
@click.option("--system", "allow_system", is_flag=True, help="Explicitly approve installation into system Python.")
def install_cmd(target: str, env_type: str, check_only: bool, allow_system: bool) -> None:
    """Safe-by-default installer for backend dependencies."""
    print_banner()
    console.print(f"Inspecting dependencies for '[bold]{target}[/bold]' (env={env_type})...\n")

    success, msg, missing = install_packages(
        target=target,
        env=env_type,
        check_only=check_only,
        allow_system=allow_system,
    )

    if success:
        print_success(msg)
    else:
        print_warning(msg)
        sys.exit(1)


@cli.command("list")
def list_cmd() -> None:
    """List all supported platforms, capabilities, and backend priority order."""
    print_banner()
    table = Table(show_header=True, header_style="bold", border_style="dim")
    table.add_column("Channel", style="bold cyan", width=14)
    table.add_column("Name", width=22)
    table.add_column("Zero-Config", width=14)
    table.add_column("Actions", width=28)
    table.add_column("Ordered Backends (Primary -> Fallbacks)")

    for ch in list_channels():
        actions_str = ", ".join([a.name for a in ch.actions])
        backends_str = " -> ".join([f"{b.id}" for b in ch.backends])
        zc_str = "[green]Yes[/green]" if ch.zero_config else "[yellow]Auth needed[/yellow]"

        table.add_row(ch.id, ch.name, zc_str, actions_str, backends_str)

    console.print(table)


@cli.group("auth")
def auth_group() -> None:
    """Manage browser session cookies for login-walled platforms."""
    pass


@auth_group.command("status")
@click.argument("platform", required=False)
def auth_status_cmd(platform: Optional[str]) -> None:
    """Check stored cookie status for a platform or all platforms."""
    if platform:
        status = get_platform_auth_status(platform)
        console.print(f"\n[bold]{status['platform'].capitalize()} Authentication:[/bold]")
        console.print(f"Status: {status['status'].value}")
        console.print(f"Cookies Stored: {status['cookie_count']}")
        console.print(f"Message: {status['message']}")
    else:
        table = Table(show_header=True, header_style="bold", border_style="dim")
        table.add_column("Platform", style="cyan", width=16)
        table.add_column("Status", width=16)
        table.add_column("Cookie Count", width=14)
        table.add_column("Details")

        for s in get_all_auth_statuses():
            stat_style = "[green]Healthy[/green]" if s["has_cookies"] else "[dim]Not configured[/dim]"
            table.add_row(s["platform"], stat_style, str(s["cookie_count"]), s["message"])
        console.print(table)


@auth_group.command("import")
@click.argument("platform")
@click.argument("file_path", type=click.Path(exists=True))
def auth_import_cmd(platform: str, file_path: str) -> None:
    """Import cookies from a Cookie-Editor JSON or cookies.txt file."""
    try:
        res = import_cookies_from_file(platform, file_path)
        print_success(f"Imported {res['cookie_count']} cookies for {res['platform']}.")
        console.print(f"[dim]Saved to: {res['saved_path']}[/dim]")
    except Exception as e:
        print_error(f"Import failed: {str(e)}")
        sys.exit(1)


@auth_group.command("delete")
@click.argument("platform")
def auth_delete_cmd(platform: str) -> None:
    """Delete stored cookies for a platform."""
    if delete_platform_cookies(platform):
        print_success(f"Deleted cookies for {platform}.")
    else:
        print_warning(f"No cookies found for {platform}.")


@cli.group("config")
def config_group() -> None:
    """Manage NetEyes configuration and backend preferences."""
    pass


@config_group.command("show")
def config_show_cmd() -> None:
    """Display current NetEyes configuration."""
    cfg = load_config()
    console.print(json.dumps(cfg, indent=2))


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set_cmd(key: str, value: str) -> None:
    """Set a configuration property (e.g. proxy, timeout_seconds)."""
    cfg = load_config()
    # Convert types if numeric
    if value.lower() in ("true", "false"):
        parsed_val: Any = value.lower() == "true"
    elif value.isdigit():
        parsed_val = int(value)
    else:
        parsed_val = value
    cfg[key] = parsed_val
    save_config(cfg)
    print_success(f"Config updated: {key} = {parsed_val}")


@config_group.command("get")
@click.argument("key")
def config_get_cmd(key: str) -> None:
    """Get a configuration property value."""
    cfg = load_config()
    val = cfg.get(key)
    console.print(f"{key}: {val}")


@config_group.command("prefer")
@click.argument("channel")
@click.argument("backend_id")
def config_prefer_cmd(channel: str, backend_id: str) -> None:
    """Set preferred backend override for a channel."""
    norm = normalize_channel_id(channel)
    set_preferred_backend(norm, backend_id)
    print_success(f"Set preferred backend for '{norm}' to '{backend_id}'.")


def main() -> None:
    """Main CLI entrypoint."""
    cli()


if __name__ == "__main__":
    main()
