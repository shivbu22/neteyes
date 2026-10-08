"""NetEyes: Give any AI agent real eyes on the internet.

A capability layer and multi-backend routing engine for AI agents.
"""

__version__ = "0.1.0"
__author__ = "NetEyes Contributors"
__license__ = "MIT"

from neteyes.models import (
    ActionSpec,
    BackendSpec,
    ChannelSpec,
    DoctorReport,
    ExecutionResult,
    HealthStatus,
)
from neteyes.router import route, run

__all__ = [
    "__version__",
    "route",
    "run",
    "ChannelSpec",
    "BackendSpec",
    "ActionSpec",
    "ExecutionResult",
    "HealthStatus",
    "DoctorReport",
]
