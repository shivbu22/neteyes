"""Capability routing layer and fallback execution engine."""

from __future__ import annotations

import time
from typing import Any, List, Optional
from neteyes.auth import get_platform_auth_status
from neteyes.backends.base import BaseBackend
from neteyes.channels import get_backends_for_channel, get_channel, normalize_channel_id
from neteyes.config import get_preferred_backend, load_config
from neteyes.models import ExecutionResult, HealthStatus, RouteResult


def get_ordered_backends(channel_id: str, backend_override: Optional[str] = None) -> List[BaseBackend]:
    """Retrieve backends for a channel ordered by priority, preferences, and health."""
    norm_id = normalize_channel_id(channel_id)
    backends = get_backends_for_channel(norm_id)
    if not backends:
        return []

    cfg = load_config()
    disabled = set(cfg.get("disabled_backends", []))
    backends = [b for b in backends if b.id not in disabled]

    if backend_override:
        # User specified an exact backend
        chosen = [b for b in backends if b.id == backend_override]
        if chosen:
            return chosen

    # Check preferred backend in config
    pref = get_preferred_backend(norm_id)
    if pref:
        backends.sort(key=lambda b: 0 if b.id == pref else b.priority)
    else:
        backends.sort(key=lambda b: b.priority)

    return backends


def route(channel_id: str, action: str, **kwargs: Any) -> RouteResult:
    """Route an agent to the best available upstream tool or command.

    Core Philosophy:
    NetEyes selects the best current backend for each platform and generates
    the exact upstream CLI / command so the agent can execute it directly.
    """
    norm_id = normalize_channel_id(channel_id)
    ch = get_channel(norm_id)
    if not ch:
        raise ValueError(f"Unknown channel '{channel_id}'. Run 'neteyes list' to view available channels.")

    backends = get_ordered_backends(norm_id)
    if not backends:
        raise RuntimeError(f"No available backends configured for channel '{channel_id}'")

    # Evaluate health of backends in order
    selected: Optional[BaseBackend] = None
    reason = ""
    fallback_order = [b.id for b in backends]

    for b in backends:
        status, msg = b.check_health()
        if status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED):
            selected = b
            reason = f"Selected '{b.name}' ({b.id}) - Health: {status.value} ({msg})"
            break

    # If all report missing dependency or requires auth, choose primary and provide instructions
    if not selected:
        selected = backends[0]
        status, msg = selected.check_health()
        reason = f"Defaulting to '{selected.name}' ({selected.id}) despite warning: {msg}"

    direct_cmd = selected.get_direct_command(action, **kwargs)

    # Auth details
    auth_info = get_platform_auth_status(norm_id)
    requires_auth = selected.requires_auth
    auth_status_str = auth_info.get("status", HealthStatus.HEALTHY).value

    usage_notes = None
    if direct_cmd:
        usage_notes = "You can run the direct_command directly in your shell for zero-overhead upstream execution."
    elif selected.requires_auth and not auth_info.get("has_cookies"):
        usage_notes = f"This backend requires login cookies. Run 'neteyes auth {norm_id} --import <cookies.json>' before execution."

    return RouteResult(
        channel_id=norm_id,
        action=action,
        selected_backend=selected.get_spec(),
        direct_command=direct_cmd,
        routing_reason=reason,
        ordered_backends=fallback_order,
        requires_auth=requires_auth,
        auth_status=auth_status_str,
        usage_notes=usage_notes,
    )


def run(channel_id: str, action: str, backend_override: Optional[str] = None, **kwargs: Any) -> ExecutionResult:
    """Execute an action through the best healthy backend with automatic fallbacks."""
    start_time = time.time()
    norm_id = normalize_channel_id(channel_id)
    ch = get_channel(norm_id)
    if not ch:
        return ExecutionResult(
            success=False,
            channel_id=channel_id,
            action=action,
            backend_id="none",
            error=f"Unknown channel '{channel_id}'. Run 'neteyes list' for all channels.",
        )

    backends = get_ordered_backends(norm_id, backend_override=backend_override)
    if not backends:
        return ExecutionResult(
            success=False,
            channel_id=norm_id,
            action=action,
            backend_id="none",
            error=f"No enabled backends found for channel '{norm_id}'",
        )

    attempted = []
    last_error = ""

    for b in backends:
        attempted.append(b.id)
        # Check health first
        status, health_msg = b.check_health()
        if status in (HealthStatus.MISSING_DEPENDENCY, HealthStatus.UNAVAILABLE):
            last_error = f"{b.name}: {health_msg}"
            continue

        if b.requires_auth:
            auth_info = get_platform_auth_status(norm_id)
            if not auth_info.get("has_cookies"):
                last_error = f"{b.name} requires cookies. Run 'neteyes auth {norm_id} --import <file>'"
                continue

        # Execute
        try:
            result = b.execute(action, **kwargs)
            if result.success:
                result.fallbacks_attempted = attempted
                return result
            else:
                last_error = f"{b.name} returned error: {result.error}"
        except Exception as e:
            last_error = f"{b.name} raised exception: {str(e)}"

    elapsed_ms = (time.time() - start_time) * 1000.0
    return ExecutionResult(
        success=False,
        channel_id=norm_id,
        action=action,
        backend_id=attempted[-1] if attempted else "none",
        error=f"All backends failed for {norm_id}:{action}. Last error: {last_error}",
        execution_time_ms=round(elapsed_ms, 2),
        fallbacks_attempted=attempted,
    )
