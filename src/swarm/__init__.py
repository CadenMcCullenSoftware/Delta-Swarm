"""Multi-agent swarm system for user-controlled workflow execution."""

__version__ = "1.0.0"

from .governance import GovernanceEngine, GovernanceViolationError

__all__ = ["GovernanceEngine", "GovernanceViolationError"]
