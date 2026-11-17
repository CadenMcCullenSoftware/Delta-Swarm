"""Unit tests for the swarm system."""

import pytest

from swarm.agent import (
    Agent,
    CoordinatorAgent,
    PlannerAgent,
    ReviewerAgent,
    WorkerAgent,
)
from swarm.gate import ApprovalGate
from swarm.message_bus import MessageBus
from swarm.record import EvidenceRecord
from swarm.swarm import Swarm
from swarm.types import (
    ActionType,
    AgentRole,
    ApprovalStatus,
    Capability,
    Reversibility,
    Task,
    TaskStatus,
)
from swarm.workflow import Workflow


def test_agent_can_handle_task():
    bus = MessageBus()
    agent = WorkerAgent("w-1", bus)
    task = Task(task_id="t-1", name="execute", command=["echo", "hi"])
    assert agent.can_handle(task) is True
    other = Task(task_id="t-2", name="plan", command=["echo", "hi"])
    assert agent.can_handle(other) is False


def test_message_bus_publish_and_subscribe():
    bus = MessageBus()
    received = []
    bus.subscribe("a-1", lambda m: received.append(m))
    bus.publish("a-2", "hello", to_agent="a-1")
    assert len(received) == 1
    assert received[0].content == "hello"


def test_workflow_dependency_order():
    wf = Workflow("wf")
    wf.add_task(Task(task_id="a", name="a", command=["a"]))
    wf.add_task(Task(task_id="b", name="b", command=["b"], depends_on=["a"]))
    wf.add_task(Task(task_id="c", name="c", command=["c"], depends_on=["a", "b"]))
    order = wf.dependency_order()
    assert order.index("a") < order.index("b")
    assert order.index("b") < order.index("c")


def test_workflow_circular_dependency():
    wf = Workflow("wf")
    wf.add_task(Task(task_id="a", name="a", command=["a"], depends_on=["b"]))
    wf.add_task(Task(task_id="b", name="b", command=["b"], depends_on=["a"]))
    with pytest.raises(ValueError):
        wf.dependency_order()


def test_workflow_ready_tasks():
    wf = Workflow("wf")
    wf.add_task(Task(task_id="a", name="a", command=["a"]))
    wf.add_task(Task(task_id="b", name="b", command=["b"], depends_on=["a"]))
    wf.mark("a", TaskStatus.COMPLETED)
    ready = wf.ready_tasks()
    assert len(ready) == 1
    assert ready[0].task_id == "b"


def test_gate_approve_and_decline():
    gate = ApprovalGate()
    gate.draft("act-1", ActionType.OTHER, "test", external_or_state_changing=True)
    gate.request_approval("act-1", "user", "scope")
    assert gate.is_approved("act-1") is False
    gate.approve("act-1")
    assert gate.is_approved("act-1") is True


def test_gate_blocks_unapproved_state_changing():
    gate = ApprovalGate()
    gate.draft("act-2", ActionType.DELETE, "delete", external_or_state_changing=True)
    gate.request_approval("act-2", "user", "scope")
    with pytest.raises(ValueError):
        gate.mark_completed("act-2")


def test_record_add_claim_and_source():
    rec = EvidenceRecord(human_author="Caden McCullen")
    rec.add_claim("c-1", "claim text", epistemic_status="direct_observation",
                  support_status="supported", uncertainty="low")
    rec.add_source("s-1", "Source Title", access_status="opened_and_reviewed")
    rec.set_attribution(human_author="Caden McCullen", attribution_basis="user_provided")
    data = rec.to_dict()
    assert data["attribution"]["human_author"] == "Caden McCullen"
    assert data["attribution"]["ai_role"] == "supporting_tool"
    assert len(data["claims"]) == 1
    assert len(data["sources"]) == 1


def test_swarm_default_agents():
    swarm = Swarm.default_swarm(name="test")
    assert "coordinator-1" in swarm.agents()
    assert "planner-1" in swarm.agents()
    assert "worker-1" in swarm.agents()
    assert "reviewer-1" in swarm.agents()


def test_swarm_run_auto_approve():
    swarm = Swarm.default_swarm(name="test", auto_approve=True)
    swarm.add_task(Task(task_id="t-1", name="execute", command=["echo", "hi"]))
    statuses = swarm.run(coordinator_id="coordinator-1")
    assert statuses["t-1"] == TaskStatus.COMPLETED


def test_swarm_run_requires_approval_blocks():
    swarm = Swarm.default_swarm(name="test", auto_approve=False)
    swarm.add_task(Task(task_id="t-1", name="execute", command=["echo", "hi"],
                        requires_approval=True))
    statuses = swarm.run(coordinator_id="coordinator-1")
    assert statuses["t-1"] == TaskStatus.BLOCKED


def test_swarm_approve_unblocks():
    swarm = Swarm.default_swarm(name="test", auto_approve=False)
    swarm.add_task(Task(task_id="t-1", name="execute", command=["echo", "hi"],
                        requires_approval=True))
    swarm.run(coordinator_id="coordinator-1")
    swarm.approve_action("action-t-1")
    task = swarm.workflow.get_task("t-1")
    assert task.status == TaskStatus.COMPLETED


def test_agent_roles():
    bus = MessageBus()
    assert PlannerAgent("p", bus).role == AgentRole.PLANNER
    assert WorkerAgent("w", bus).role == AgentRole.WORKER
    assert ReviewerAgent("r", bus).role == AgentRole.REVIEWER
    assert CoordinatorAgent("c", bus).role == AgentRole.COORDINATOR


def test_capability_dataclass():
    cap = Capability(name="execute", description="run tasks")
    assert cap.name == "execute"
