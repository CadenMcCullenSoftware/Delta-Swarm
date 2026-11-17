"""Unit tests for the swarm system with compliance/correctness separation."""

import pytest

from swarm.agent import (
    Agent,
    CoordinatorAgent,
    PlannerAgent,
    ReviewerAgent,
    WorkerAgent,
)
from swarm.cli import parse_nlp
from swarm.gate import ApprovalGate
from swarm.record import EvidenceRecord
from swarm.swarm import Swarm
from swarm.types import (
    ActionType,
    AgentRole,
    ApprovalStatus,
    Capability,
    ComplianceStatus,
    CorrectnessStatus,
    Reversibility,
    Task,
    TaskStatus,
)
from swarm.workflow import Workflow


def test_agent_can_handle_task():
    from swarm.message_bus import MessageBus
    bus = MessageBus()
    agent = WorkerAgent("w-1", bus)
    task = Task(task_id="t-1", name="execute", command=["echo", "hi"])
    assert agent.can_handle(task) is True
    other = Task(task_id="t-2", name="plan", command=["echo", "hi"])
    assert agent.can_handle(other) is False


def test_message_bus_publish_and_subscribe():
    from swarm.message_bus import MessageBus
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


def test_gate_approve_sets_compliance_not_correctness():
    """Compliance != Correctness: approve sets compliance=COMPLIANT, correctness=NOT_ASSESSED."""
    gate = ApprovalGate()
    gate.draft("act-1", ActionType.OTHER, "test", external_or_state_changing=True)
    gate.request_approval("act-1", "user", "scope")
    gate.approve("act-1")
    action = gate.get("act-1")
    assert action.status == ApprovalStatus.APPROVED
    assert action.compliance_status == ComplianceStatus.COMPLIANT
    assert action.correctness_status == CorrectnessStatus.NOT_ASSESSED  # AI does not self-certify


def test_gate_blocks_unapproved_state_changing():
    gate = ApprovalGate()
    gate.draft("act-2", ActionType.DELETE, "delete", external_or_state_changing=True)
    gate.request_approval("act-2", "user", "scope")
    with pytest.raises(ValueError):
        gate.mark_completed("act-2")


def test_commander_can_set_correctness_independent_of_compliance():
    """Commander enforces correctness separately from compliance."""
    gate = ApprovalGate()
    gate.draft("act-3", ActionType.OTHER, "test", external_or_state_changing=True)
    gate.request_approval("act-3", "user", "scope")
    gate.approve("act-3")  # compliance satisfied
    # Commander marks correctness separately
    gate.record_correctness("act-3", CorrectnessStatus.INCORRECT, "evidence unsupported")
    action = gate.get("act-3")
    assert action.compliance_status == ComplianceStatus.COMPLIANT
    assert action.correctness_status == CorrectnessStatus.INCORRECT


def test_compliant_but_incorrect_is_possible():
    """Compliance does not equal correctness: a compliant action can be incorrect."""
    gate = ApprovalGate()
    gate.draft("act-4", ActionType.OTHER, "test", external_or_state_changing=True)
    gate.request_approval("act-4", "user", "scope")
    gate.approve("act-4")
    gate.record_correctness("act-4", CorrectnessStatus.INCORRECT, "result wrong despite procedure followed")
    action = gate.get("act-4")
    assert action.compliance_status == ComplianceStatus.COMPLIANT
    assert action.correctness_status == CorrectnessStatus.INCORRECT


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


def test_ai_self_certified_correct_remains_false():
    """AI never self-certifies correctness."""
    rec = EvidenceRecord(human_author="Caden McCullen")
    rec.set_reasoning(summary="some reasoning")
    assert rec.record.reasoning.ai_self_certified_correct is False


def test_commander_review_sets_correctness():
    rec = EvidenceRecord(human_author="Caden McCullen")
    rec.commander_review_task(
        review_id="r-1",
        reviewed_by="commander",
        task_id="t-1",
        correctness="correct",
        compliance="compliant",
        reasoning="evidence supported",
        notes="ok",
    )
    summary = rec.compliance_correctness_summary()
    reviews = summary["evidence_reviews"]
    assert len(reviews) == 1
    assert reviews[0]["correctness"] == "correct"
    assert reviews[0]["compliance"] == "compliant"
    assert reviews[0]["commander_override"] is False


def test_swarm_default_agents():
    swarm = Swarm.default_swarm(name="test")
    assert "coordinator-1" in swarm.agents()
    assert "planner-1" in swarm.agents()
    assert "worker-1" in swarm.agents()
    assert "reviewer-1" in swarm.agents()


def test_swarm_run_auto_approve_compliance_only():
    """auto_approve sets compliance=COMPLIANT but correctness=NOT_ASSESSED."""
    swarm = Swarm.default_swarm(name="test", auto_approve=True)
    swarm.add_task(Task(task_id="t-1", name="execute", command=["echo", "hi"],
                        requires_approval=True))
    statuses = swarm.run(coordinator_id="coordinator-1")
    assert statuses["t-1"] == TaskStatus.COMPLETED
    task = swarm.workflow.get_task("t-1")
    assert task.compliance_status == ComplianceStatus.COMPLIANT
    assert task.correctness_status == CorrectnessStatus.NOT_ASSESSED
    assert task.commander_reviewed is False


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
    assert task.compliance_status == ComplianceStatus.COMPLIANT
    assert task.correctness_status == CorrectnessStatus.NOT_ASSESSED


def test_swarm_commander_review_task_sets_correctness():
    swarm = Swarm.default_swarm(name="test", auto_approve=True)
    swarm.add_task(Task(task_id="t-1", name="execute", command=["echo", "hi"]))
    swarm.run(coordinator_id="coordinator-1")
    swarm.commander_review_task(
        review_id="r-1",
        reviewed_by="commander",
        task_id="t-1",
        correctness="correct",
        compliance="compliant",
        reasoning="output matches expected",
        notes="verified",
    )
    task = swarm.workflow.get_task("t-1")
    assert task.commander_reviewed is True
    assert task.correctness_status == CorrectnessStatus.CORRECT
    assert task.compliance_status == ComplianceStatus.COMPLIANT


def test_agent_roles():
    from swarm.message_bus import MessageBus
    bus = MessageBus()
    assert PlannerAgent("p", bus).role == AgentRole.PLANNER
    assert WorkerAgent("w", bus).role == AgentRole.WORKER
    assert ReviewerAgent("r", bus).role == AgentRole.REVIEWER
    assert CoordinatorAgent("c", bus).role == AgentRole.COORDINATOR


def test_capability_dataclass():
    cap = Capability(name="execute", description="run tasks")
    assert cap.name == "execute"


def test_summary_includes_compliance_and_correctness():
    swarm = Swarm.default_swarm(name="test", auto_approve=True)
    swarm.add_task(Task(task_id="t-1", name="execute", command=["echo", "hi"],
                        requires_approval=True))
    swarm.run(coordinator_id="coordinator-1")
    summary = swarm.summary()
    task_info = summary["tasks"]["t-1"]
    assert task_info["status"] == "completed"
    assert task_info["compliance"] == "compliant"
    assert task_info["correctness"] == "not_assessed"
    assert task_info["commander_reviewed"] is False
    assert summary["record"]["reasoning"]["ai_self_certified_correct"] is False


def test_nlp_add_and_run():
    swarm = Swarm.default_swarm(name="wf")
    p = parse_nlp("add task build command echo hello")
    assert p["command"] == "add"
    assert p["task_id"] == "build"
    from swarm.cli import handle_nlp
    out = handle_nlp(swarm, p)
    assert "Added task build" in out
    p2 = parse_nlp("run workflow wf auto-approve")
    out2 = handle_nlp(swarm, p2)
    assert "auto_approve=True" in out2 or "auto_approve = True" in out2 or "Ran workflow wf" in out2
