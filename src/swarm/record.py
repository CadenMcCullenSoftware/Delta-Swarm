"""Evidence record keeping aligned with the agent-design schema."""

from __future__ import annotations

from .types import SwarmRecord


class EvidenceRecord:
    """Structured record of claims, sources, artifacts, actions, and attribution."""

    def __init__(self, human_author: str | None = None,
                 attribution_basis: str = "not_specified") -> None:
        self.record = SwarmRecord()
        self.record.attribution.human_author = human_author
        self.record.attribution.attribution_basis = attribution_basis

    def add_claim(self, claim_id: str, text: str,
                  epistemic_status: str = "unknown",
                  support_status: str = "unverified",
                  uncertainty: str = "") -> None:
        from .types import Claim, EpistemicStatus, SupportStatus
        self.record.claims.append(Claim(
            claim_id=claim_id,
            text=text,
            epistemic_status=EpistemicStatus(epistemic_status),
            support_status=SupportStatus(support_status),
            uncertainty=uncertainty,
        ))

    def add_source(self, source_id: str, title: str,
                   access_status: str = "not_checked",
                   source_category: str = "other") -> None:
        from .types import Source
        self.record.sources.append(Source(
            source_id=source_id,
            title=title,
            access_status=access_status,
            source_category=source_category,
        ))

    def add_artifact(self, artifact_id: str, kind: str, identifier: str,
                     risk_review: str = "") -> None:
        from .types import Artifact
        self.record.artifacts.append(Artifact(
            artifact_id=artifact_id,
            kind=kind,
            identifier=identifier,
            risk_review=risk_review,
        ))

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

    def set_reasoning(self, summary: str = "", assumptions: list[str] | None = None,
                      unknowns: list[str] | None = None) -> None:
        from .types import Reasoning
        self.record.reasoning = Reasoning(
            summary=summary,
            assumptions=assumptions or [],
            unknowns=unknowns or [],
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
