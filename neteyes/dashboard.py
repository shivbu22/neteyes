"""Interactive terminal dashboard for NetEyes.

Provides a real-time, high-fidelity monitoring view of internet capability channels,
backend statuses, cookie authentication health, proxy pools, and MCP readiness.
"""

from __future__ import annotations

import platform
import sys
import time
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from neteyes import __version__
from neteyes.channels import list_channels
from neteyes.config import get_neteyes_home, load_config
from neteyes.doctor import run_doctor
from neteyes.models import HealthStatus
from neteyes.auth import get_all_auth_statuses
from neteyes.utils.proxy import get_proxy_strategy, list_proxies


console = Console()


def build_header() -> Panel:
    """Build dashboard header with environment and system telemetry."""
    cfg = load_config()
    home = get_neteyes_home()
    sys_info = f"Python {platform.python_version()} | {platform.system()} {platform.release()} ({platform.machine()})"
    home_str = str(home)
    
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="right", ratio=1)

    left_text = Text.from_markup(
        f"[bold cyan]NetEyes Agent Intelligence Console[/bold cyan] [bold white]v{__version__}[/bold white]\n"
        f"[dim]{sys_info}[/dim]"
    )
    right_text = Text.from_markup(
        f"[dim]NetEyes Home:[/dim] [yellow]{home_str}[/yellow]\n"
        f"[dim]Timeout:[/dim] [white]{cfg.get('timeout_seconds', 15)}s[/white]  |  [dim]Format:[/dim] [white]{cfg.get('output_format', 'markdown')}[/white]"
    )
    grid.add_row(left_text, right_text)

    return Panel(grid, border_style="cyan", padding=(0, 1))


def build_channels_table(doctor_report) -> Table:
    """Build comprehensive channels status table."""
    table = Table(title="Internet Capabilities & Channel Health", title_style="bold green", expand=True, border_style="dim")
    table.add_column("Channel", style="bold cyan", width=14)
    table.add_column("Status", width=16)
    table.add_column("Active Primary Backend", width=26)
    table.add_column("Auth Type", width=16)
    table.add_column("Available Actions")

    channel_diags = {d.name: d for d in doctor_report.diagnostics if d.category == "channel"}
    auth_statuses = {s["platform"]: s for s in get_all_auth_statuses()}

    for ch in list_channels():
        diag = channel_diags.get(ch.id)
        if diag:
            if diag.status == HealthStatus.HEALTHY:
                stat = "[bold green]● HEALTHY[/bold green]"
            elif diag.status == HealthStatus.DEGRADED:
                stat = "[bold yellow]▲ DEGRADED[/bold yellow]"
            elif diag.status == HealthStatus.REQUIRES_AUTH:
                stat = "[bold yellow]▲ AUTH REQ[/bold yellow]"
            else:
                stat = "[bold red]✖ OFFLINE[/bold red]"
            active_b = f"`{diag.active_backend}`" if diag.active_backend else "[dim]None[/dim]"
        else:
            stat = "[dim]UNKNOWN[/dim]"
            active_b = "[dim]N/A[/dim]"

        auth_s = auth_statuses.get(ch.id)
        if ch.zero_config:
            auth_col = "[green]Zero-Config[/green]"
        elif auth_s and auth_s["has_cookies"]:
            auth_col = f"[cyan]Cookies ({auth_s['cookie_count']})[/cyan]"
        else:
            auth_col = "[yellow]Auth Needed[/yellow]"

        actions_str = ", ".join([a.name for a in ch.actions])
        table.add_row(ch.name, stat, active_b, auth_col, actions_str)

    return table


def build_proxy_panel() -> Panel:
    """Build proxy pool monitoring panel."""
    proxies = list_proxies()
    strat = get_proxy_strategy()

    lines = [f"[bold]Rotation Strategy:[/bold] [green]{strat}[/green]"]
    lines.append(f"[bold]Active Pool Size:[/bold] {len(proxies)} proxies\n")

    if not proxies:
        lines.append("[dim]No proxies active (Direct connection).[/dim]")
        lines.append("[dim]Add with: neteyes proxy add <url>[/dim]")
    else:
        for idx, p in enumerate(proxies[:4], 1):
            ptype = p.split("://")[0].upper() if "://" in p else "HTTP"
            lines.append(f"  [cyan]{idx}.[/cyan] [dim]{ptype}[/dim] {p}")
        if len(proxies) > 4:
            lines.append(f"  [dim]... and {len(proxies) - 4} more[/dim]")

    return Panel("\n".join(lines), title="[bold cyan]Proxy & Anti-Blocking Pool[/bold cyan]", border_style="cyan", padding=(0, 1))


def build_integrations_panel() -> Panel:
    """Build agent & protocol readiness panel."""
    lines = [
        "[bold green]✔ MCP Server:[/bold green] Available ([dim]neteyes mcp[/dim])",
        "[bold green]✔ Schema Generator:[/bold green] Available ([dim]neteyes schema[/dim])",
        "[bold green]✔ Safe Fallback Cascade:[/bold green] Multi-tier auto fallback",
        "[bold green]✔ Local DPAPI Cookie Sync:[/bold green] Available ([dim]neteyes auth sync[/dim])",
        "",
        "[dim]Direct CLI Run: neteyes run <channel> <action> <args>[/dim]",
        "[dim]Routing Diagnostic: neteyes route <channel> <action>[/dim]",
    ]
    return Panel("\n".join(lines), title="[bold green]AI Agent Tooling Readiness[/bold green]", border_style="green", padding=(0, 1))


def render_dashboard() -> Layout:
    """Compose complete dashboard layout."""
    doctor_report = run_doctor()
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=4),
        Layout(name="channels", ratio=2),
        Layout(name="footer", size=9),
    )
    layout["header"].update(build_header())
    layout["channels"].update(build_channels_table(doctor_report))
    
    footer_split = Layout()
    footer_split.split_row(
        Layout(build_proxy_panel(), name="proxies", ratio=1),
        Layout(build_integrations_panel(), name="agent", ratio=1),
    )
    layout["footer"].update(footer_split)
    return layout


def run_dashboard(watch: bool = False, interval: float = 3.0) -> None:
    """Run dashboard either as one-shot snapshot or live auto-refreshing terminal."""
    if not watch:
        console.print(render_dashboard())
        return

    console.print("[dim]Starting NetEyes Live Dashboard (Press Ctrl+C to exit)...[/dim]")
    try:
        with Live(render_dashboard(), console=console, screen=True, refresh_per_second=2) as live:
            while True:
                time.sleep(interval)
                live.update(render_dashboard())
    except KeyboardInterrupt:
        pass
