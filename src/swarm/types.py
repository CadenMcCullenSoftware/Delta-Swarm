"""Core type definitions for the swarm system.

Includes explicit separation between compliance (procedure followed) and
correctness (evidence-supported result), per the principle that compliance
does not equal correctness and that correctness is enforced by the human
commander, not the AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentRole(str, Enum):
    PLANNER = "planner"
    WORKER = "worker"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ActionType(str, Enum):
    DRAFT_ONLY = "draft_only"
    READ_ONLY = "read_only"
    EXTERNAL_MESSAGE = "external_message"
    PUBLISH = "publish"
    PURCHASE = "purchase"
    DELETE = "delete"
    SUBMIT = "submit"
    ACCESS_CHANGE = "access_change"
    DATA_DISCLOSURE = "data_disclosure"
    OTHER = "other"


class ApprovalStatus(str, Enum):
    NOT_STARTED = "not_started"
    DRAFTED = "drafted"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    DECLINED = "declined"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class Reversibility(str, Enum):
    REVERSIBLE = "reversible"
    PARTLY_REVERSIBLE = "partly_reversible"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"


class ComplianceStatus(str, Enum):
    """Whether the required procedure was followed (approval, scope, gating)."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"


class CorrectnessStatus(str, Enum):
    """Whether the result is evidence-supported. Enforced by the commander, not the AI."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNCERTAIN = "uncertain"
    NOT_ASSESSED = "not_assessed"


class EpistemicStatus(str, Enum):
    SOURCE_REPORTED_FACT = "source_reported_fact"
    DIRECT_OBSERVATION = "direct_observation"
    CALCULATION = "calculation"
    INFERENCE = "inference"
    CAUSAL_HYPOTHESIS = "causal_hypothesis"
    OPINION_OR_RECOMMENDATION = "opinion_or_recommendation"
    UNKNOWN = "unknown"


class SupportStatus(str, Enum):
    SUPPORTED = "supported"
    PARTLY_SUPPORTED = "partly_supported"
    UNSUPPORTED = "unsupported"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    UNVERIFIED = "unverified"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class Capability:
    name: str
    description: str = ""


@dataclass
class AgentRecord:
    agent_id: str
    role: AgentRole
    capabilities: list[Capability] = field(default_factory=list)
    active: bool = True


@dataclass
class Task:
    task_id: str
    name: str
    command: list[str]
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str | None = None
    result: str | None = None
    error: str | None = None
    working_directory: str | None = None
    timeout: int | None = None
    failure_handling: str = "stop"
    requires_approval: bool = False
    # Compliance vs correctness separation
    compliance_status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    correctness_status: CorrectnessStatus = CorrectnessStatus.NOT_ASSESSED
    commander_review_required: bool = True
    commander_reviewed: bool = False
    commander_notes: str | None = None
    commander_reviewed_at: str | None = None


@dataclass
class Message:
    message_id: str
    from_agent: str
    to_agent: str | None
    content: str
    timestamp: str = ""
    reply_to: str | None = None


@dataclass
class ApprovalGate:
    required: bool = False
    explicit: bool = False
    prior_to_execution: bool = False
    approver: str | None = None
    approved_scope: str | None = None
    approval_timestamp: str | None = None
    status: ApprovalStatus = ApprovalStatus.NOT_STARTED


@dataclass
class Action:
    action_id: str
    action_type: ActionType
    external_or_state_changing: bool = False
    status: ApprovalStatus = ApprovalStatus.NOT_STARTED
    approval: ApprovalGate = field(default_factory=ApprovalGate)
    action_summary: str = ""
    target: str | None = None
    inputs: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    reversibility: Reversibility = Reversibility.UNKNOWN
    # Compliance vs correctness separation
    compliance_status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    correctness_status: CorrectnessStatus = CorrectnessStatus.NOT_ASSESSED
    compliance_reasoning: str = ""
    correctness_reasoning: str = ""
    commander_reviewed: bool = False
    commander_reviewed_at: str | None = None


@dataclass
class Claim:
    claim_id: str
    text: str
    epistemic_status: EpistemicStatus = EpistemicStatus.UNKNOWN
    support_status: SupportStatus = SupportStatus.UNVERIFIED
    source_ids: list[str] = field(default_factory=list)
    uncertainty: str = ""
    verification_criterion: str | None = None
    limitations: list[str] = field(default_factory=list)


@dataclass
class Source:
    source_id: str
    title: str
    author_or_publisher: str | None = None
    url: str | None = None
    publication_date: str | None = None
    accessed_date: str | None = None
    access_status: str = "not_checked"
    source_category: str = "other"
    claims_supported: list[str] = field(default_factory=list)
    support_summary: str = ""
    relevant_passage_or_result: str | None = None
    units_and_baseline_checked: bool = False
    limitations: list[str] = field(default_factory=list)


@dataclass
class Artifact:
    artifact_id: str
    kind: str
    identifier: str
    existence_status: str = "not_checked"
    inspection_status: str = "not_inspected"
    execution_status: str = "not_run"
    purpose: str | None = None
    inputs_outputs_dependencies: list[str] = field(default_factory=list)
    risk_review: str = ""
    dry_run_or_sandbox_used: bool = False
    result_summary: str | None = None


@dataclass
class EvidenceReview:
    """A human commander's review separating compliance from correctness."""

    review_id: str
    reviewed_by: str
    reviewed_at: str
    target_id: str
    target_type: str  # "task" or "action" or "claim"
    compliance_assessment: ComplianceStatus
    correctness_assessment: CorrectnessStatus
    reasoning: str
    commander_override: bool = False
    notes: str | None = None


@dataclass
class Reasoning:
    summary: str = ""
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    alternatives_considered: list[str] = field(default_factory=list)
    ai_self_certified_correct: bool = False  # must remain False; AI never self-certifies


@dataclass
class Evaluation:
    status: str = "not_evaluated"
    benchmark_claim: str = ""
    benchmark_details: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)


@dataclass
class Attribution:
    human_author: str | None = None
    attribution_basis: str = "not_specified"
    ai_role: str = "supporting_tool"
    notes: str | None = None


@dataclass
class SwarmRecord:
    schema_version: str = "1.0.0"
    task: dict[str, Any] = field(default_factory=dict)
    claims: list[Claim] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    reasoning: Reasoning = field(default_factory=Reasoning)
    actions: list[Action] = field(default_factory=list)
    evaluation: Evaluation = field(default_factory=Evaluation)
    attribution: Attribution = field(default_factory=Attribution)
    evidence_reviews: list[EvidenceReview] = field(default_factory=list)
