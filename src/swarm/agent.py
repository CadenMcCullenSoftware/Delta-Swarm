"""Base agent and role-specific agent implementations."""

from __future__ import annotations

from .message_bus import MessageBus
from .types import AgentRecord, AgentRole, Capability, Task, TaskStatus


class Agent:
    """Base swarm agent with a role, capabilities, and message bus access."""

    def __init__(self, agent_id: str, role: AgentRole,
                 bus: MessageBus, capabilities: list[Capability] | None = None) -> None:
        self.agent_id = agent_id
        self.role = role
        self.bus = bus
        self.record = AgentRecord(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities or [],
        )
        bus.subscribe(agent_id, self._handle_message)
        self._inbox: list = []

    def _handle_message(self, message) -> None:
        self._inbox.append(message)

    def can_handle(self, task: Task) -> bool:
        return any(c.name == task.name for c in self.record.capabilities)

    def assign(self, task: Task) -> None:
        self.record.active = True

    def execute(self, task: Task) -> tuple[str, str | None]:
        """Execute a task and return (result, error)."""
        raise NotImplementedError

    def report(self, task_id: str, result: str, error: str | None = None) -> None:
        self.bus.publish(
            from_agent=self.agent_id,
            content=f"Task {task_id}: result={result} error={error}",
        )


class PlannerAgent(Agent):
    """Decomposes workflows into tasks and assigns them to capable agents."""

    def __init__(self, agent_id: str, bus: MessageBus) -> None:
        super().__init__(agent_id, AgentRole.PLANNER, bus,
                         capabilities=[Capability("plan", "Decompose workflows into tasks")])

    def execute(self, task: Task) -> tuple[str, str | None]:
        return f"Planned {task.name}", None


class WorkerAgent(Agent):
    """Executes assigned tasks through the command runner."""

    def __init__(self, agent_id: str, bus: MessageBus) -> None:
        super().__init__(agent_id, AgentRole.WORKER, bus,
                         capabilities=[Capability("execute", "Execute workflow tasks")])

    def execute(self, task: Task) -> tuple[str, str | None]:
        return f"Executed {task.name}", None


class ReviewerAgent(Agent):
    """Reviews completed task results for correctness and completeness."""

    def __init__(self, agent_id: str, bus: MessageBus) -> None:
        super().__init__(agent_id, AgentRole.REVIEWER, bus,
                         capabilities=[Capability("review", "Review task results")])

    def execute(self, task: Task) -> tuple[str, str | None]:
        return f"Reviewed {task.name}", None


class CoordinatorAgent(Agent):
    """Coordinates task assignment across the swarm based on agent capabilities."""

    def __init__(self, agent_id: str, bus: MessageBus) -> None:
        super().__init__(agent_id, AgentRole.COORDINATOR, bus,
                         capabilities=[Capability("coordinate", "Assign tasks to agents")])

    def execute(self, task: Task) -> tuple[str, str | None]:
        return f"Coordinated {task.name}", None
