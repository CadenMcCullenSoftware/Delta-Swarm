"""Evidence record keeping aligned with the agent-design schema.

Separates compliance (procedure followed) from correctness (evidence-supported).
Correctness is enforced by the human commander; the AI does not self-certify.
"""

from __future__ import annotations

from .types import (
    ActionType,
    ApprovalStatus,
    ComplianceStatus,
    CorrectnessStatus,
    EpistemicStatus,
    EvidenceReview,
    Reversibility,
    Source,
    SupportStatus,
    SwarmRecord,
)


class EvidenceRecord:
    """Structured record of claims, sources, artifacts, actions, and attribution.

    Every claim carries epistemic and support metadata; every source carries
    access status and limitations. Compliance and correctness are tracked
    separately: compliance means the procedure was followed, correctness means
    the result is evidence-supported and is assessed by the human commander.
    """

    def __init__(self, human_author: str | None = None,
                 attribution_basis: str = "not_specified") -> None:
        self.record = SwarmRecord()
        self.record.attribution.human_author = human_author
        self.record.attribution.attribution_basis = attribution_basis

    # ---------- claims ----------
    def add_claim(self, claim_id: str, text: str,
                  epistemic_status: str = "unknown",
                  support_status: str = "unverified",
                  uncertainty: str = "") -> None:
        self.record.claims.append(
            self._claim(claim_id, text, epistemic_status, support_status, uncertainty)
        )

    def _claim(self, claim_id: str, text: str, epistemic_status: str,
               support_status: str, uncertainty: str):
        from .types import Claim
        return Claim(
            claim_id=claim_id,
            text=text,
            epistemic_status=EpistemicStatus(epistemic_status),
            support_status=SupportStatus(support_status),
            uncertainty=uncertainty,
        )

    def update_claim_support(self, claim_id: str,
                             support_status: str,
                             uncertainty: str) -> None:
        from .types import SupportStatus
        for claim in self.record.claims:
            if claim.claim_id == claim_id:
                claim.support_status = SupportStatus(support_status)
                claim.uncertainty = uncertainty
                return
        raise ValueError(f"Unknown claim {claim_id}")

    # ---------- sources ----------
    def add_source(self, source_id: str, title: str,
                   access_status: str = "not_checked",
                   source_category: str = "other") -> None:
        self.record.sources.append(
            self._source(source_id, title, access_status, source_category)
        )

    def _source(self, source_id: str, title: str,
                access_status: str, source_category: str):
        from .types import Source
        return Source(
            source_id=source_id,
            title=title,
            access_status=access_status,
            source_category=source_category,
        )

    # ---------- artifacts ----------
    def add_artifact(self, artifact_id: str, kind: str, identifier: str,
                     risk_review: str = "") -> None:
        from .types import Artifact
        self.record.artifacts.append(Artifact(
            artifact_id=artifact_id,
            kind=kind,
            identifier=identifier,
            risk_review=risk_review,
        ))

    # ---------- actions ----------
    def add_action(self, action_id: str, action_type: str,
                   external_or_state_changing: bool = False,
                   summary: str = "", target: str | None = None) -> None:
        from .types import Action, ActionType
        self.record.actions.append(Action(
            action_id=action_id,
            action_type=ActionType(action_type),
            external_or_state_changing=external_or_state_changing,
            action_summary=summary,
            target=target,
        ))

    # ---------- evidence reviews (compliance vs correctness) ----------
    def add_evidence_review(self, review_id: str, reviewed_by: str,
                            target_id: str, target_type: str,
                            compliance_assessment: str,
                            correctness_assessment: str,
                            reasoning: str,
                            commander_override: bool = False,
                            notes: str | None = None) -> None:
        from .types import EvidenceReview
        self.record.evidence_reviews.append(EvidenceReview(
            review_id=review_id,
            reviewed_by=reviewed_by,
            reviewed_at="",  # set by swarm at review time
            target_id=target_id,
            target_type=target_type,
            compliance_assessment=ComplianceStatus(compliance_assessment),
            correctness_assessment=CorrectnessStatus(correctness_assessment),
            reasoning=reasoning,
            commander_override=commander_override,
            notes=notes,
        ))

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
        from .types import CorrectnessStatus, ComplianceStatus
        self.add_evidence_review(
            review_id=review_id,
            reviewed_by=reviewed_by,
            target_id=task_id,
            target_type="task",
            compliance_assessment=compliance,
            correctness_assessment=correctness,
            reasoning=reasoning,
            commander_override=commander_override,
            notes=notes,
        )
        self._apply_task_review(task_id, ComplianceStatus(compliance),
                                CorrectnessStatus(correctness), reviewed_by)

    def _apply_task_review(self, task_id: str, compliance: ComplianceStatus,
                           correctness: CorrectnessStatus, reviewed_by: str) -> None:
        # Mirror review onto the action record if one exists
        action_id = f"action-{task_id}"
        for action in self.record.actions:
            if action.action_id == action_id:
                action.compliance_status = compliance
                action.correctness_status = correctness
                action.commander_reviewed = True
                action.commander_reviewed_at = ""

    def set_reasoning(self, summary: str = "",
                      assumptions: list[str] | None = None,
                      unknowns: list[str] | None = None) -> None:
        from .types import Reasoning
        self.record.reasoning = Reasoning(
            summary=summary,
            assumptions=assumptions or [],
            unknowns=unknowns or [],
            # AI never self-certifies correctness
            ai_self_certified_correct=False,
        )

    def set_attribution(self, human_author: str | None = None,
                        attribution_basis: str = "not_specified",
                        notes: str | None = None) -> None:
        self.record.attribution.human_author = human_author
        self.record.attribution.attribution_basis = attribution_basis
        self.record.attribution.notes = notes
        self.record.attribution.ai_role = "supporting_tool"

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self.record)

    def compliance_correctness_summary(self) -> dict:
        """Return a summary separating compliance from correctness."""
        tasks = {}
        for action in self.record.actions:
            tasks[action.action_id] = {
                "approval": action.status.value,
                "compliance": action.compliance_status.value,
                "correctness": action.correctness_status.value,
                "commander_reviewed": action.commander_reviewed,
            }
        claims = {}
        for claim in self.record.claims:
            claims[claim.claim_id] = {
                "support": claim.support_status.value,
                "uncertainty": claim.uncertainty,
            }
        return {
            "attribution": {
                "human_author": self.record.attribution.human_author,
                "ai_role": self.record.attribution.ai_role,
            },
            "reasoning": {
                "summary": self.record.reasoning.summary,
                "ai_self_certified_correct": self.record.reasoning.ai_self_certified_correct,
            },
            "tasks": tasks,
            "claims": claims,
            "evidence_reviews": [
                {
                    "review_id": r.review_id,
                    "reviewed_by": r.reviewed_by,
                    "target_id": r.target_id,
                    "target_type": r.target_type,
                    "compliance": r.compliance_assessment.value,
                    "correctness": r.correctness_assessment.value,
                    "commander_override": r.commander_override,
                    "reasoning": r.reasoning,
                }
                for r in self.record.evidence_reviews
            ],
        }
