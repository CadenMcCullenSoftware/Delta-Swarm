"""Pre-action approval gate for state-changing operations.

Separates compliance (procedure followed: approval, scope, prior-to-execution)
from correctness (evidence-supported result). Approval means the procedure was
followed; it does NOT mean the result is correct. Correctness is enforced by
the human commander, not the AI.
"""

from __future__ import annotations

from .types import (
    Action,
    ActionType,
    ApprovalGate,
    ApprovalStatus,
    ComplianceStatus,
    CorrectnessStatus,
    Reversibility,
)


class ApprovalGate:
    """Validates and tracks approval state for actions before execution.

    Compliance = procedure followed (approval obtained, scope confirmed,
    prior_to_execution respected).
    Correctness = evidence-supported result (NOT asserted by this gate).
    """

    def __init__(self) -> None:
        self._actions: dict[str, Action] = {}

    def draft(
        self,
        action_id: str,
        action_type: ActionType,
        summary: str,
        target: str | None = None,
        external_or_state_changing: bool = False,
        inputs: list[str] | None = None,
        permissions: list[str] | None = None,
        effects: list[str] | None = None,
        side_effects: list[str] | None = None,
        reversibility: Reversibility = Reversibility.UNKNOWN,
    ) -> Action:
        action = Action(
            action_id=action_id,
            action_type=action_type,
            external_or_state_changing=external_or_state_changing,
            action_summary=summary,
            target=target,
            inputs=inputs or [],
            permissions=permissions or [],
            effects=effects or [],
            side_effects=side_effects or [],
            reversibility=reversibility,
        )
        self._actions[action_id] = action
        return action

    def request_approval(self, action_id: str, approver: str, scope: str) -> ApprovalGate:
        action = self._actions[action_id]
        action.approval.required = True
        action.approval.explicit = True
        action.approval.prior_to_execution = True
        action.approval.approver = approver
        action.approval.approved_scope = scope
        action.status = ApprovalStatus.AWAITING_APPROVAL
        return action.approval

    def approve(self, action_id: str) -> None:
        """Mark an action as approved (procedure followed).

        Approval means compliance with the pre-action gate; it does NOT
        assert correctness of the result. Correctness remains
        CorrectnessStatus.NOT_ASSESSED until the human commander reviews.
        """
        action = self._actions[action_id]
        if action.status != ApprovalStatus.AWAITING_APPROVAL:
            raise ValueError(f"Action {action_id} is not awaiting approval")
        action.status = ApprovalStatus.APPROVED
        action.compliance_status = ComplianceStatus.COMPLIANT
        # correctness_status is intentionally left NOT_ASSESSED

    def decline(self, action_id: str) -> None:
        action = self._actions[action_id]
        action.status = ApprovalStatus.DECLINED
        action.compliance_status = ComplianceStatus.NON_COMPLIANT

    def mark_completed(self, action_id: str) -> None:
        action = self._actions.get(action_id)
        if action is None:
            raise ValueError(f"Unknown action {action_id}")
        if action.external_or_state_changing and action.status != ApprovalStatus.APPROVED:
            raise ValueError(
                f"Action {action_id} must be approved before completion "
                f"(compliance gate not satisfied)"
            )
        action.status = ApprovalStatus.COMPLETED

    def record_compliance(self, action_id: str, compliant: bool, reasoning: str = "") -> None:
        """Record compliance assessment independent of approval status."""
        action = self._actions[action_id]
        action.compliance_status = (
            ComplianceStatus.COMPLIANT if compliant else ComplianceStatus.NON_COMPLIANT
        )
        action.compliance_reasoning = reasoning

    def record_correctness(
        self, action_id: str, correct: CorrectnessStatus, reasoning: str = ""
    ) -> None:
        """Record correctness assessment. Only the human commander should call this.

        The AI must not self-certify correctness.
        """
        action = self._actions[action_id]
        action.correctness_status = correct
        action.correctness_reasoning = reasoning

    def is_approved(self, action_id: str) -> bool:
        action = self._actions.get(action_id)
        if action is None:
            return False
        if not action.external_or_state_changing:
            return True
        return action.status == ApprovalStatus.APPROVED

    def is_compliant(self, action_id: str) -> bool:
        action = self._actions.get(action_id)
        if action is None:
            return False
        return action.compliance_status == ComplianceStatus.COMPLIANT

    def is_correct(self, action_id: str) -> bool:
        action = self._actions.get(action_id)
        if action is None:
            return False
        return action.correctness_status == CorrectnessStatus.CORRECT

    def get(self, action_id: str) -> Action | None:
        return self._actions.get(action_id)

    def all(self) -> list[Action]:
        return list(self._actions.values())
