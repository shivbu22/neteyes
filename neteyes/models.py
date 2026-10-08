"""Core data models and type contracts for NetEyes."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status for backends and system components."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    REQUIRES_AUTH = "requires_auth"
    MISSING_DEPENDENCY = "missing_dependency"


class BackendType(str, Enum):
    """Type of backend adapter."""
    PYTHON_MODULE = "python_module"
    CLI_BINARY = "cli_binary"
    DIRECT_API = "direct_api"
    HYBRID = "hybrid"


class ActionSpec(BaseModel):
    """Specification of an action supported by a channel."""
    name: str = Field(description="Unique action name within the channel, e.g. 'extract', 'search'")
    description: str = Field(description="Brief description of what this action achieves")
    parameters: Dict[str, str] = Field(default_factory=dict, description="Name -> type/description")
    example_args: List[str] = Field(default_factory=list, description="Example arguments for routing and CLI")


class BackendSpec(BaseModel):
    """Specification of a backend adapter."""
    id: str = Field(description="Unique backend identifier, e.g. 'trafilatura', 'jina_reader'")
    name: str = Field(description="Human-friendly name of the backend")
    priority: int = Field(default=10, description="Priority rank (lower number = higher priority)")
    description: str = Field(description="Summary of capabilities and approach")
    backend_type: BackendType = Field(default=BackendType.DIRECT_API)
    requires_auth: bool = Field(default=False, description="Whether this backend mandates user login/cookies")
    dependencies: List[str] = Field(default_factory=list, description="Required Python packages or CLI binaries")
    cli_template: Optional[str] = Field(default=None, description="CLI command template if agent can run directly")


class ChannelSpec(BaseModel):
    """Specification of an internet channel/platform."""
    id: str = Field(description="Unique channel id, e.g. 'web', 'youtube', 'twitter', 'reddit'")
    name: str = Field(description="Human readable name of the channel")
    description: str = Field(description="Description of what this channel enables")
    actions: List[ActionSpec] = Field(default_factory=list)
    backends: List[BackendSpec] = Field(default_factory=list)
    login_walled: bool = Field(default=False, description="Whether this channel generally requires login")
    zero_config: bool = Field(default=True, description="Whether this channel works out of the box without keys")


class ExecutionResult(BaseModel):
    """Result of executing an action through a backend."""
    success: bool
    channel_id: str
    action: str
    backend_id: str
    data: Optional[Any] = None
    markdown: Optional[str] = None
    raw: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    fallbacks_attempted: List[str] = Field(default_factory=list)


class RouteResult(BaseModel):
    """Information returned when an agent requests capability routing."""
    channel_id: str
    action: str
    selected_backend: BackendSpec
    direct_command: Optional[str] = Field(
        default=None,
        description="The exact command line the agent can execute directly in shell"
    )
    routing_reason: str = Field(description="Explanation of why this backend was selected")
    ordered_backends: List[str] = Field(default_factory=list, description="Full fallback chain")
    requires_auth: bool = False
    auth_status: Optional[str] = None
    usage_notes: Optional[str] = None


class DiagnosticItem(BaseModel):
    """Individual diagnostic finding in DoctorReport."""
    category: str = Field(description="Category: 'python', 'cli_binary', 'backend', 'cookie', 'network'")
    name: str
    status: HealthStatus
    message: str
    active_backend: Optional[str] = Field(default=None, description="Currently active backend ID for channels")
    fix_prescription: Optional[str] = None


class DoctorReport(BaseModel):
    """System-wide health check report."""
    timestamp: str
    python_version: str
    in_virtualenv: bool
    os_name: str
    healthy_channels: int
    degraded_channels: int
    unavailable_channels: int
    diagnostics: List[DiagnosticItem] = Field(default_factory=list)
    fix_prescriptions: List[str] = Field(default_factory=list)
