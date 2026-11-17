"""Pre-action approval gate for state-changing operations."""

from __future__ import annotations

from .types import Action, ActionType, ApprovalGate, ApprovalStatus, Reversibility


class ApprovalGate:
    """Validates and tracks approval state for actions before execution."""

    def __init__(self) -> None:
        self._actions: dict[str, Action] = {}

    def draft(self, action_id: str, action_type: ActionType,
              summary: str, target: str | None = None,
              external_or_state_changing: bool = False,
              inputs: list[str] | None = None,
              permissions: list[str] | None = None,
              effects: list[str] | None = None,
              side_effects: list[str] | None = None,
              reversibility: Reversibility = Reversibility.UNKNOWN) -> Action:
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

    def request_approval(self, action_id: str, approver: str,
                         scope: str) -> ApprovalGate:
        action = self._actions[action_id]
        action.approval.required = True
        action.approval.explicit = True
        action.approval.prior_to_execution = True
        action.approval.approver = approver
        action.approval.approved_scope = scope
        action.status = ApprovalStatus.AWAITING_APPROVAL
        return action.approval

    def approve(self, action_id: str) -> None:
        action = self._actions[action_id]
        if action.status != ApprovalStatus.AWAITING_APPROVAL:
            raise ValueError(f"Action {action_id} is not awaiting approval")
        action.status = ApprovalStatus.APPROVED

    def decline(self, action_id: str) -> None:
        action = self._actions[action_id]
        action.status = ApprovalStatus.DECLINED

    def mark_completed(self, action_id: str) -> None:
        action = self._actions[action_id]
        if action.external_or_state_changing and action.status != ApprovalStatus.APPROVED:
            raise ValueError(f"Action {action_id} must be approved before completion")
        action.status = ApprovalStatus.COMPLETED

    def is_approved(self, action_id: str) -> bool:
        action = self._actions.get(action_id)
        if action is None:
            return False
        if not action.external_or_state_changing:
            return True
        return action.status == ApprovalStatus.APPROVED

    def get(self, action_id: str) -> Action | None:
        return self._actions.get(action_id)

    def all(self) -> list[Action]:
        return list(self._actions.values())
