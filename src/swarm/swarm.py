"""Swarm coordinator: orchestrates agents across workflow tasks."""

from __future__ import annotations

import subprocess
from typing import Callable

from .agent import Agent, CoordinatorAgent, PlannerAgent, ReviewerAgent, WorkerAgent
from .gate import ApprovalGate
from .message_bus import MessageBus
from .record import EvidenceRecord
from .types import ActionType, Reversibility, TaskStatus
from .workflow import Workflow


class Swarm:
    """Multi-agent swarm that executes workflows under user-controlled gating."""

    def __init__(self, name: str, human_author: str | None = None,
                 auto_approve: bool = False) -> None:
        self.name = name
        self.bus = MessageBus()
        self.workflow = Workflow(name)
        self.gate = ApprovalGate()
        self.record = EvidenceRecord(human_author=human_author)
        self._agents: dict[str, Agent] = {}
        self._auto_approve = auto_approve
        self._on_action: Callable[[str, str], None] | None = None

    def add_agent(self, agent: Agent) -> None:
        self._agents[agent.agent_id] = agent

    def agent(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def agents(self) -> dict[str, Agent]:
        return dict(self._agents)

    def add_task(self, task) -> None:
        self.workflow.add_task(task)
        self.record.add_artifact(
            artifact_id=f"task-{task.task_id}",
            kind="task",
            identifier=task.task_id,
            risk_review="Workflow task definition",
        )

    def set_action_handler(self, handler: Callable[[str, str], None]) -> None:
        self._on_action = handler

    def _run_command(self, task) -> tuple[str, str | None]:
        try:
            proc = subprocess.run(
                task.command,
                cwd=task.working_directory,
                capture_output=True,
                text=True,
                timeout=task.timeout,
            )
            output = proc.stdout.strip()
            if proc.returncode != 0:
                return output, proc.stderr.strip() or f"exit code {proc.returncode}"
            return output, None
        except FileNotFoundError as exc:
            return "", f"Command not found: {exc}"
        except subprocess.TimeoutExpired as exc:
            return "", f"Timeout expired: {exc}"

    def _run_task_command(self, task, agent: Agent) -> None:
        self.workflow.mark(task.task_id, TaskStatus.IN_PROGRESS,
                           assigned_to=agent.agent_id)
        result, error = agent.execute(task)
        command_result, command_error = self._run_command(task)
        if command_error:
            error = command_error
        if error:
            self.workflow.mark(task.task_id, TaskStatus.FAILED, error=error)
        else:
            combined = result
            if command_result:
                combined = f"{result}\n{command_result}"
            self.workflow.mark(task.task_id, TaskStatus.COMPLETED, result=combined)
        agent.report(task.task_id, combined if not error else "", error)

    def _execute_task(self, task, agent: Agent) -> None:
        if task.requires_approval:
            self.gate.draft(
                action_id=f"action-{task.task_id}",
                action_type=ActionType.OTHER,
                summary=task.name,
                target=task.working_directory,
                external_or_state_changing=True,
                inputs=list(task.command),
                reversibility=Reversibility.UNKNOWN,
            )
            self.gate.request_approval(f"action-{task.task_id}", "user", task.name)
            if self._auto_approve:
                self.gate.approve(f"action-{task.task_id}")
            else:
                self.workflow.mark(task.task_id, TaskStatus.BLOCKED)
                if self._on_action:
                    self._on_action(f"action-{task.task_id}", task.name)
                return
        self._run_task_command(task, agent)

    def run(self, coordinator_id: str | None = None) -> dict[str, TaskStatus]:
        """Execute the workflow in dependency order."""
        order = self.workflow.dependency_order()
        statuses: dict[str, TaskStatus] = {}
        for task_id in order:
            task = self.workflow.get_task(task_id)
            assert task is not None
            deps_done = all(
                self.workflow.get_task(d).status == TaskStatus.COMPLETED
                for d in task.depends_on
            )
            if not deps_done:
                self.workflow.mark(task_id, TaskStatus.BLOCKED)
                statuses[task_id] = TaskStatus.BLOCKED
                continue
            agent = self._select_agent(task)
            if agent is None:
                self.workflow.mark(task_id, TaskStatus.FAILED,
                                   error="No capable agent available")
                statuses[task_id] = TaskStatus.FAILED
                continue
            self._execute_task(task, agent)
            statuses[task_id] = task.status
            if task.status == TaskStatus.FAILED and task.failure_handling == "stop":
                break
        return statuses

    def _select_agent(self, task) -> Agent | None:
        for agent in self._agents.values():
            if agent.record.active and agent.can_handle(task):
                return agent
        for agent in self._agents.values():
            if agent.role.value == "worker" and agent.record.active:
                return agent
        return None

    def approve_action(self, action_id: str) -> None:
        self.gate.approve(action_id)
        task_id = action_id.replace("action-", "", 1)
        task = self.workflow.get_task(task_id)
        if task and task.status == TaskStatus.BLOCKED:
            agent = self._select_agent(task)
            if agent:
                self._run_task_command(task, agent)

    def decline_action(self, action_id: str) -> None:
        self.gate.decline(action_id)
        task_id = action_id.replace("action-", "", 1)
        task = self.workflow.get_task(task_id)
        if task:
            self.workflow.mark(task_id, TaskStatus.CANCELLED)

    def summary(self) -> dict:
        return {
            "swarm": self.name,
            "agents": {aid: a.role.value for aid, a in self._agents.items()},
            "tasks": {tid: t.status.value for tid, t in self.workflow.tasks().items()},
            "actions": {a.action_id: a.status.value for a in self.gate.all()},
            "record": self.record.to_dict(),
        }

    @classmethod
    def default_swarm(cls, name: str = "default",
                      human_author: str | None = None,
                      auto_approve: bool = False) -> "Swarm":
        swarm = cls(name=name, human_author=human_author, auto_approve=auto_approve)
        swarm.add_agent(CoordinatorAgent("coordinator-1", swarm.bus))
        swarm.add_agent(PlannerAgent("planner-1", swarm.bus))
        swarm.add_agent(WorkerAgent("worker-1", swarm.bus))
        swarm.add_agent(ReviewerAgent("reviewer-1", swarm.bus))
        return swarm
