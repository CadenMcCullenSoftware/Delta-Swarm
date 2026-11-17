"""Multi-agent swarm system for user-controlled workflow execution."""

__version__ = "1.0.0"

from .agent_logic import AgentLogicEnforcer, GovernanceValidationError
from .governance import GovernanceEngine, GovernanceViolationError

__all__ = [
    "AgentLogicEnforcer",
    "GovernanceEngine",
    "GovernanceValidationError",
    "GovernanceViolationError",
]

from .governance import GovernanceEngine, GovernanceViolationError

__all__ = ["GovernanceEngine", "GovernanceViolationError"]
