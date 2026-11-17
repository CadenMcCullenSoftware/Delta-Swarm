"""Agent logic enforcer.

Integrates the three governing principles from docs/agent_governance_schema.json
with the swarm's GovernanceEngine:

1. Compliance vs. Correctness — behavioral compliance (literal prompt
   adherence / syntactic conformity) does not equal correctness.
2. Evidence-Based Trust — trust is grounded strictly in verifiable evidence
   and step-by-step reasoning; self-critique or sycophantic agreement do not
   constitute verification.
3. Commander Authority — correctness and final operational authorization are
   enforced by the human commander; the AI is a supportive tool and never
   self-certifies correctness or self-authorizes state-changing actions.
"""

from __future__ import annotations

from typing import Any

from .governance import (
    CorrectnessStatus,
    GovernanceEngine,
    GovernanceViolationError,
)

# Backward-compatible alias matching the agent-governance schema naming.
GovernanceValidationError = GovernanceViolationError


class AgentLogicEnforcer:
    """Middleware enforcing governance rules on agent proposals and actions.

    The AI is explicitly NOT the commander. It may evaluate proposals and
    gather evidence, but correctness and execution authorization rest solely
    with the human commander.
    """

    def __init__(self, engine: GovernanceEngine, commander_present: bool = True) -> None:
        self.engine = engine
        # AI is explicitly not the commander; commander_present reflects whether
        # a human commander is available to enforce correctness/authorization.
        self.commander_present = commander_present

    # ------------------------------------------------------------------
    # Principle 1 & 2: evaluate a proposal against evidence
    # ------------------------------------------------------------------
    def evaluate_correctness(
        self,
        proposal: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Evaluate whether a proposal is correct based on verifiable evidence.

        Compliance (syntax_valid / instruction_followed) is tracked separately
        from correctness. A proposal may be compliant yet incorrect. Correctness
        requires primary-source evidence and causal soundness; the AI does not
        self-certify it.
        """
        syntax_compliant = bool(proposal.get("syntax_valid", False))
        instruction_followed = bool(proposal.get("instruction_followed", False))

        if syntax_compliant and instruction_followed:
            compliance_status = "COMPLIANT_SURFACE"
        else:
            compliance_status = "NON_COMPLIANT"

        # Evidence-based trust: only primary, verified sources count.
        verifiable_evidence = [
            e for e in evidence
            if e.get("is_primary_source") and e.get("verified")
        ]
        evidence_sufficient = len(verifiable_evidence) == len(evidence) and len(evidence) > 0
        causally_sound = bool(proposal.get("causally_sound", False))

        is_correct = evidence_sufficient and causally_sound

        # Register the claim in the governance engine as UNVERIFIED until the
        # commander reviews. The AI does not self-certify support.
        claim_id = proposal.get("claim_id", f"claim-{abs(hash(str(proposal))) % 100000}")
        self.engine.add_claim(
            claim_id=claim_id,
            text=str(proposal.get("text", proposal.get("action_name", ""))),
            epistemic_status=(
                "direct_observation" if evidence_sufficient else "inference"
            ),
            source_ids=[e.get("source_id", "") for e in verifiable_evidence if e.get("source_id")],
            reasoning_steps=[
                {
                    "step_id": f"{claim_id}-step-1",
                    "description": "Evaluate proposal against evidence",
                    "evidence_ids": [str(i) for i in range(len(verifiable_evidence))],
                    "conclusion": "correct" if is_correct else "incorrect",
                    "uncertainty": "low" if is_correct else "high",
                }
            ],
            uncertainty="low" if is_correct else "high",
            verification_criterion="primary_source_verification",
        )

        if not is_correct:
            return {
                "status": "REJECTED",
                "reason": "Trust failure: insufficient primary evidence or proposal not causally sound.",
                "compliance_status": compliance_status,
                "is_correct": False,
                "correctness_status": "not_assessed",
                "ai_self_certified_correct": False,
                "claim_id": claim_id,
                "note": "Correctness remains NOT_ASSESSED pending commander review.",
            }

        return {
            "status": "EVALUATED",
            "compliance_status": compliance_status,
            "is_correct": True,
            "correctness_status": "not_assessed",
            "ai_self_certified_correct": False,
            "evidence_count": len(verifiable_evidence),
            "claim_id": claim_id,
            "note": "Evidence and causality pass the AI pre-check; commander review still required for correctness and authorization.",
        }

    # ------------------------------------------------------------------
    # Principle 3: commander authority over execution
    # ------------------------------------------------------------------
    def execute_action(
        self,
        action_payload: dict[str, Any],
        evaluation_result: dict[str, Any],
        commander_approval: bool | None,
    ) -> dict[str, Any]:
        """Enforce commander authority over state-changing execution.

        The AI cannot self-authorize. Even a correct proposal requires explicit
        commander approval before execution. Without approval, execution pauses
        and a proposal is returned.
        """
        if not evaluation_result.get("is_correct", False):
            raise GovernanceViolationError(
                principle="hierarchical_authority",
                detail="Action is compliant with prompts but fails epistemic correctness.",
            )

        if not commander_approval or not self.commander_present:
            return {
                "action_status": "PAUSED_AWAITING_COMMANDER",
                "proposal": action_payload,
                "message": (
                    "Action is verified correct but requires explicit approval "
                    "from the Commander before execution."
                ),
                "authorized_by": None,
            }

        return {
            "action_status": "EXECUTED",
            "action_payload": action_payload,
            "authorized_by": "HUMAN_COMMANDER",
        }
