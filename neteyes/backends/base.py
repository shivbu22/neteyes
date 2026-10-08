"""Abstract base class for all NetEyes backend adapters."""

from __future__ import annotations

import shlex
import shutil
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from neteyes.models import BackendSpec, BackendType, ExecutionResult, HealthStatus


def safe_quote(arg: Any) -> str:
    """Safely escape shell argument against command injection."""
    s = str(arg if arg is not None else "").strip()
    return shlex.quote(s)


class BaseBackend(ABC):
    """Abstract base class for all capability backends."""

    id: str = "base"
    name: str = "Base Backend"
    priority: int = 100
    description: str = "Base capability adapter"
    backend_type: BackendType = BackendType.DIRECT_API
    requires_auth: bool = False
    dependencies: List[str] = []

    def get_spec(self) -> BackendSpec:
        """Return the BackendSpec model representation."""
        return BackendSpec(
            id=self.id,
            name=self.name,
            priority=self.priority,
            description=self.description,
            backend_type=self.backend_type,
            requires_auth=self.requires_auth,
            dependencies=self.dependencies,
        )

    def is_binary_available(self, binary_name: str) -> bool:
        """Check if an executable binary exists on the system PATH."""
        return shutil.which(binary_name) is not None

    def is_python_module_available(self, module_name: str) -> bool:
        """Check if a Python module is importable."""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False

    @abstractmethod
    def check_health(self) -> Tuple[HealthStatus, str]:
        """Perform a quick, non-destructive health check.

        Returns:
            Tuple of (HealthStatus, diagnostic_message)
        """
        pass

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        """Return the upstream CLI command if the agent can execute it directly."""
        return None

    @abstractmethod
    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        """Execute the requested action.

        Args:
            action: Action verb (e.g. 'extract', 'search', 'subtitles')
            **kwargs: Action parameters

        Returns:
            ExecutionResult containing structured data and clean markdown.
        """
        pass

    def _make_result(
        self,
        success: bool,
        channel_id: str,
        action: str,
        start_time: float,
        data: Optional[Any] = None,
        markdown: Optional[str] = None,
        raw: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Helper to construct standard ExecutionResult."""
        elapsed_ms = (time.time() - start_time) * 1000.0
        return ExecutionResult(
            success=success,
            channel_id=channel_id,
            action=action,
            backend_id=self.id,
            data=data,
            markdown=markdown,
            raw=raw,
            execution_time_ms=round(elapsed_ms, 2),
            metadata=metadata or {},
            error=error,
        )
