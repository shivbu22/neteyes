"""Rich console output helpers.

Adheres to NetEyes design principles:
- Clean, modern, minimalist aesthetics
- Minimal emojis in CLI output
- Clear structural hierarchy, tables, panels, and syntax highlighting
"""

from __future__ import annotations

import sys
from typing import Any, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Ensure standard streams use UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Initialize Rich console with safe UTF-8 encoding
console = Console(highlight=False, legacy_windows=False)
err_console = Console(stderr=True, highlight=False, legacy_windows=False)


def print_banner() -> None:
    """Print the subtle, clean NetEyes header banner."""
    title = Text("NetEyes", style="bold cyan")
    tagline = Text(" — Give any AI agent real eyes on the internet", style="dim")
    banner_text = Text.assemble(title, tagline)
    console.print(banner_text)
    console.print()


def print_header(text: str) -> None:
    """Print a section header."""
    console.print(f"\n[bold]{text}[/bold]")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]![/yellow] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    err_console.print(f"[red]✗[/red] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]•[/blue] {message}")


def create_table(columns: List[str], title: Optional[str] = None) -> Table:
    """Create a styled Rich table with minimal borders."""
    table = Table(
        title=title,
        show_header=True,
        header_style="bold",
        border_style="dim",
        expand=False,
    )
    for col in columns:
        table.add_column(col)
    return table


def print_panel(content: Any, title: Optional[str] = None, border_style: str = "dim") -> None:
    """Print content enclosed in a clean panel."""
    panel = Panel(content, title=title, border_style=border_style, padding=(1, 2))
    console.print(panel)
