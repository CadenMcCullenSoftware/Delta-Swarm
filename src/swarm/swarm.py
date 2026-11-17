"""Swarm coordinator: orchestrates agents across workflow tasks.

Enforces the separation between compliance (procedure followed: approval,
scope, prior-to-execution) and correctness (evidence-supported result).
Compliance does not equal correctness. Correctness is enforced by the human
commander; the AI does not self-certify correctness.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import Callable

from .agent import Agent, CoordinatorAgent, PlannerAgent, ReviewerAgent, WorkerAgent
from .gate import ApprovalGate
from .message_bus import MessageBus
from .record import EvidenceRecord
from .types import (
    ActionType,
    ComplianceStatus,
    CorrectnessStatus,
    Reversibility,
    TaskStatus,
)
from .workflow import Workflow


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        # auto_approve is a commander opt-in for COMPLIANCE only. It never
        # self-certifies correctness.
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
        # Task execution complete: compliance may be set, but correctness is
        # intentionally left NOT_ASSESSED until the human commander reviews.
        # The AI does not self-certify correctness.

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
                # Commander-opted compliance only. Correctness stays
                # NOT_ASSESSED; the AI does not self-certify.
                self.gate.approve(f"action-{task.task_id}")
                task.compliance_status = ComplianceStatus.COMPLIANT
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
        """Approve a pending action (compliance gate satisfied).

        Approval means the procedure was followed. Correctness is NOT
        asserted; it remains NOT_ASSESSED until the human commander reviews.
        """
        self.gate.approve(action_id)
        task_id = action_id.replace("action-", "", 1)
        task = self.workflow.get_task(task_id)
        if task:
            task.compliance_status = ComplianceStatus.COMPLIANT
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

    def commander_review_task(self, review_id: str, reviewed_by: str,
                              task_id: str, correctness: str,
                              compliance: str = "compliant",
                              reasoning: str = "",
                              notes: str | None = None,
                              commander_override: bool = False) -> None:
        """Human commander enforces correctness on a task.

        The AI must not call this to self-certify. Only the human commander
        may mark a task correct/incorrect/uncertain.
        """
        from .types import ComplianceStatus, CorrectnessStatus

        task = self.workflow.get_task(task_id)
        if task is None:
            raise ValueError(f"Unknown task {task_id}")

        self.record.commander_review_task(
            review_id=review_id,
            reviewed_by=reviewed_by,
            task_id=task_id,
            correctness=correctness,
            compliance=compliance,
            reasoning=reasoning,
            notes=notes,
            commander_override=commander_override,
        )

        task.commander_reviewed = True
        task.commander_notes = notes
        task.commander_reviewed_at = _utc_now()
        task.compliance_status = ComplianceStatus(compliance)
        task.correctness_status = CorrectnessStatus(correctness)

        # Mirror onto the action record if present
        action_id = f"action-{task_id}"
        action = self.gate.get(action_id)
        if action:
            action.compliance_status = ComplianceStatus(compliance)
            action.correctness_status = CorrectnessStatus(correctness)
            action.commander_reviewed = True
            action.commander_reviewed_at = _utc_now()

    def commander_review_action(self, review_id: str, reviewed_by: str,
                                action_id: str, correctness: str,
                                compliance: str = "compliant",
                                reasoning: str = "",
                                notes: str | None = None,
                                commander_override: bool = False) -> None:
        """Human commander enforces correctness on an action."""
        from .types import ComplianceStatus, CorrectnessStatus

        action = self.gate.get(action_id)
        if action is None:
            raise ValueError(f"Unknown action {action_id}")

        action.compliance_status = ComplianceStatus(compliance)
        action.correctness_status = CorrectnessStatus(correctness)
        action.commander_reviewed = True
        action.commander_reviewed_at = _utc_now()

        self.record.add_evidence_review(
            review_id=review_id,
            reviewed_by=reviewed_by,
            target_id=action_id,
            target_type="action",
            compliance_assessment=compliance,
            correctness_assessment=correctness,
            reasoning=reasoning,
            commander_override=commander_override,
            notes=notes,
        )

    def summary(self) -> dict:
        return {
            "swarm": self.name,
            "agents": {aid: a.role.value for aid, a in self._agents.items()},
            "tasks": {
                tid: {
                    "status": t.status.value,
                    "compliance": t.compliance_status.value,
                    "correctness": t.correctness_status.value,
                    "commander_reviewed": t.commander_reviewed,
                }
                for tid, t in self.workflow.tasks().items()
            },
            "actions": {
                a.action_id: {
                    "approval": a.status.value,
                    "compliance": a.compliance_status.value,
                    "correctness": a.correctness_status.value,
                    "commander_reviewed": a.commander_reviewed,
                }
                for a in self.gate.all()
            },
            "record": self.record.compliance_correctness_summary(),
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
