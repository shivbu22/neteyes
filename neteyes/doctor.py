"""Diagnostic engine and health checker for NetEyes."""

from __future__ import annotations

import datetime
import os
import platform
import shutil
import sys
from typing import Dict, List, Tuple
from neteyes.auth import get_all_auth_statuses, get_platform_auth_status
from neteyes.channels import CHANNEL_REGISTRY, get_backends_for_channel
from neteyes.models import DiagnosticItem, DoctorReport, HealthStatus


def is_in_virtualenv() -> bool:
    """Detect whether Python is executing inside a virtual environment."""
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix) or hasattr(sys, "real_prefix")


def run_doctor() -> DoctorReport:
    """Run comprehensive system health checks across environment, binaries, packages, and channels."""
    diagnostics: List[DiagnosticItem] = []
    prescriptions: List[str] = []

    # 1. Python Environment Check
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        diagnostics.append(
            DiagnosticItem(
                category="environment",
                name="Python Version",
                status=HealthStatus.HEALTHY,
                message=f"Python {py_ver} (meets requirement >= 3.10)",
            )
        )
    else:
        diagnostics.append(
            DiagnosticItem(
                category="environment",
                name="Python Version",
                status=HealthStatus.UNAVAILABLE,
                message=f"Python {py_ver} is unsupported. NetEyes requires Python 3.10+",
                fix_prescription="Upgrade to Python 3.10 or newer.",
            )
        )
        prescriptions.append("Upgrade Python to 3.10 or newer.")

    # Virtual environment check
    in_venv = is_in_virtualenv()
    if in_venv:
        diagnostics.append(
            DiagnosticItem(
                category="environment",
                name="Virtual Environment",
                status=HealthStatus.HEALTHY,
                message=f"Active virtual environment detected ({sys.prefix})",
            )
        )
    else:
        diagnostics.append(
            DiagnosticItem(
                category="environment",
                name="Virtual Environment",
                status=HealthStatus.DEGRADED,
                message="Running in system Python environment (not in a venv)",
                fix_prescription="Consider creating a dedicated virtualenv: python -m venv .venv",
            )
        )

    # 2. Key Upstream CLI Binaries
    cli_binaries = {
        "gh": ("GitHub official CLI", "Install GitHub CLI: https://cli.github.com/ or 'winget install GitHub.cli'"),
        "yt-dlp": ("Video and subtitle downloader", "Install via pip: pip install yt-dlp"),
        "curl": ("Standard HTTP transfer utility", "Install curl on your system"),
    }

    for binary, (desc, fix) in cli_binaries.items():
        if shutil.which(binary):
            diagnostics.append(
                DiagnosticItem(
                    category="cli_binary",
                    name=binary,
                    status=HealthStatus.HEALTHY,
                    message=f"Found on system PATH ({desc})",
                )
            )
        else:
            diagnostics.append(
                DiagnosticItem(
                    category="cli_binary",
                    name=binary,
                    status=HealthStatus.DEGRADED,
                    message=f"Not found on PATH ({desc})",
                    fix_prescription=fix,
                )
            )

    # 3. Python Package Dependencies
    key_packages = {
        "httpx": "pip install httpx",
        "rich": "pip install rich",
        "pydantic": "pip install pydantic",
        "trafilatura": "pip install trafilatura",
        "youtube_transcript_api": "pip install youtube-transcript-api",
        "duckduckgo_search": "pip install duckduckgo-search",
        "feedparser": "pip install feedparser",
        "praw": "pip install praw",
    }

    for pkg, install_cmd in key_packages.items():
        try:
            mod = __import__(pkg)
            version = getattr(mod, "__version__", "installed")
            diagnostics.append(
                DiagnosticItem(
                    category="package",
                    name=pkg,
                    status=HealthStatus.HEALTHY,
                    message=f"Installed (v{version})",
                )
            )
        except ImportError:
            status = HealthStatus.MISSING_DEPENDENCY if pkg in ("httpx", "rich", "pydantic") else HealthStatus.DEGRADED
            diagnostics.append(
                DiagnosticItem(
                    category="package",
                    name=pkg,
                    status=status,
                    message=f"Package '{pkg}' not installed",
                    fix_prescription=f"Run: {install_cmd}",
                )
            )
            prescriptions.append(f"Install package {pkg}: {install_cmd}")

    # 4. Channel Health Checks
    healthy_ch_count = 0
    degraded_ch_count = 0
    unavail_ch_count = 0

    for ch_id, ch_class in CHANNEL_REGISTRY.items():
        backends = get_backends_for_channel(ch_id)
        channel_status = HealthStatus.UNAVAILABLE
        channel_notes = []

        has_healthy_backend = False
        for b in backends:
            b_status, b_msg = b.check_health()
            if b_status == HealthStatus.HEALTHY:
                has_healthy_backend = True
            elif b_status == HealthStatus.REQUIRES_AUTH:
                channel_notes.append(f"{b.id}: requires session cookies")
            elif b_status == HealthStatus.MISSING_DEPENDENCY:
                channel_notes.append(f"{b.id}: missing dependencies")

        healthy_backends = [b for b in backends if b.check_health()[0] == HealthStatus.HEALTHY]
        if healthy_backends:
            channel_status = HealthStatus.HEALTHY
            healthy_ch_count += 1
            primary_name = healthy_backends[0].name
            summary_note = f"Ready for routing (via {primary_name})"
        elif any(b.check_health()[0] == HealthStatus.DEGRADED for b in backends):
            channel_status = HealthStatus.DEGRADED
            degraded_ch_count += 1
            summary_note = "; ".join(channel_notes) if channel_notes else "Degraded performance"
        elif any(b.check_health()[0] == HealthStatus.REQUIRES_AUTH for b in backends):
            channel_status = HealthStatus.REQUIRES_AUTH
            degraded_ch_count += 1
            summary_note = "Requires session cookies"
        else:
            channel_status = HealthStatus.UNAVAILABLE
            unavail_ch_count += 1
            summary_note = "; ".join(channel_notes) if channel_notes else "No operational backends"

        fix_p = None
        if channel_status == HealthStatus.REQUIRES_AUTH:
            fix_p = f"Import cookies for {ch_id}: neteyes auth {ch_id} --import <file.json>"
            prescriptions.append(fix_p)
        elif channel_status in (HealthStatus.DEGRADED, HealthStatus.UNAVAILABLE) and channel_notes:
            fix_p = f"Install missing backends for {ch_id}: neteyes install {ch_id}"
            prescriptions.append(fix_p)
        diagnostics.append(
            DiagnosticItem(
                category="channel",
                name=ch_id,
                status=channel_status,
                message=f"{ch_class.name} — {summary_note}",
                fix_prescription=fix_p,
            )
        )

    # Deduplicate prescriptions
    unique_prescriptions = list(dict.fromkeys(prescriptions))

    return DoctorReport(
        timestamp=datetime.datetime.now().isoformat(),
        python_version=py_ver,
        in_virtualenv=in_venv,
        os_name=platform.platform(),
        healthy_channels=healthy_ch_count,
        degraded_channels=degraded_ch_count,
        unavailable_channels=unavail_ch_count,
        diagnostics=diagnostics,
        fix_prescriptions=unique_prescriptions,
    )
