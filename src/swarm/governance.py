"""Swarm Governance Engine.

Formal enforcement of the three governing principles defined in
``docs/governance.schema.json``:

1. **Compliance vs. Correctness** — Compliance (procedure followed: approval,
   scope, prior-to-execution) is tracked separately from Correctness
   (evidence-supported result). Compliance does NOT imply correctness.
2. **Evidence-Based Trust** — Every assertion/claim must carry explicit
   evidence (source_ids) and step-by-step reasoning (reasoning_steps). Trust
   is derived from traceable logic, not probabilistic confidence.
3. **Hierarchical Authority** — The Commander (human user / supervisory
   system) is the SOLE authority for enforcing correctness. The AI is a
   subordinate executor that proposes results for validation; it must never
   self-certify correctness (``ai_self_certified_correct`` is always False).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .types import (
    ComplianceStatus,
    CorrectnessStatus,
    EpistemicStatus,
    SupportStatus,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


AI_ROLE = "supporting_tool"


# ---------------------------------------------------------------------------
# Governance violations
# ---------------------------------------------------------------------------

class GovernanceViolationError(Exception):
    """Raised when the AI attempts to violate a governing principle."""

    def __init__(self, principle: str, detail: str) -> None:
        super().__init__(f"[{principle}] {detail}")
        self.principle = principle
        self.detail = detail


# ---------------------------------------------------------------------------
# Data records (plain dicts, schema-aligned)
# ---------------------------------------------------------------------------

@dataclass
class ClaimRecord:
    claim_id: str
    text: str
    epistemic_status: str
    support_status: str = SupportStatus.UNVERIFIED
    source_ids: list[str] = field(default_factory=list)
    reasoning_steps: list[dict] = field(default_factory=list)
    uncertainty: str = ""
    verification_criterion: str | None = None
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "epistemic_status": self.epistemic_status,
            "support_status": self.support_status,
            "source_ids": list(self.source_ids),
            "reasoning_steps": list(self.reasoning_steps),
            "uncertainty": self.uncertainty,
            "verification_criterion": self.verification_criterion,
            "limitations": list(self.limitations),
        }


@dataclass
class SourceRecord:
    source_id: str
    title: str
    access_status: str = "not_checked"
    source_category: str = "other"
    author_or_publisher: str | None = None
    url: str | None = None
    claims_supported: list[str] = field(default_factory=list)
    support_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "access_status": self.access_status,
            "source_category": self.source_category,
            "author_or_publisher": self.author_or_publisher,
            "url": self.url,
            "claims_supported": list(self.claims_supported),
            "support_summary": self.support_summary,
        }


@dataclass
class ActionRecord:
    action_id: str
    action_type: str
    external_or_state_changing: bool = False
    compliance_status: str = ComplianceStatus.NOT_ASSESSED
    correctness_status: str = CorrectnessStatus.NOT_ASSESSED
    compliance_reasoning: str = ""
    correctness_reasoning: str = ""
    commander_reviewed: bool = False
    commander_reviewed_at: str | None = None
    reversibility: str = "unknown"
    effects: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "external_or_state_changing": self.external_or_state_changing,
            "compliance_status": self.compliance_status,
            "correctness_status": self.correctness_status,
            "compliance_reasoning": self.compliance_reasoning,
            "correctness_reasoning": self.correctness_reasoning,
            "commander_reviewed": self.commander_reviewed,
            "commander_reviewed_at": self.commander_reviewed_at,
            "reversibility": self.reversibility,
            "effects": list(self.effects),
            "side_effects": list(self.side_effects),
        }


@dataclass
class EvidenceReviewRecord:
    review_id: str
    reviewed_by: str
    reviewed_at: str
    target_id: str
    target_type: str  # "task" | "action" | "claim"
    compliance_assessment: str
    correctness_assessment: str
    reasoning: str
    commander_override: bool = False
    notes: str | None = None

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "compliance_assessment": self.compliance_assessment,
            "correctness_assessment": self.correctness_assessment,
            "reasoning": self.reasoning,
            "commander_override": self.commander_override,
            "notes": self.notes,
        }


@dataclass
class AttributionRecord:
    human_author: str | None = None
    attribution_basis: str = "not_specified"
    ai_role: str = AI_ROLE
    notes: str | None = None

    def to_dict(self) -> dict:
        return {
            "human_author": self.human_author,
            "attribution_basis": self.attribution_basis,
            "ai_role": self.ai_role,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Governance Engine
# ---------------------------------------------------------------------------

class GovernanceEngine:
    """Enforces the three governing principles.

    The engine is the runtime manifestation of
    ``docs/governance.schema.json``. It separates compliance from correctness,
    requires evidence for trust, and reserves correctness enforcement for the
    Commander. The AI is a subordinate executor: it may propose results and
    claims, but it may never self-certify correctness.
    """

    def __init__(self, human_author: str | None = None,
                 schema_path: str | None = None) -> None:
        self.human_author = human_author
        self.schema_path = schema_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "docs", "governance.schema.json"
        )
        self.schema = self._load_schema()

        # State
        self.claims: dict[str, ClaimRecord] = {}
        self.sources: dict[str, SourceRecord] = {}
        self.actions: dict[str, ActionRecord] = {}
        self.reviews: dict[str, EvidenceReviewRecord] = {}
        self.attribution = AttributionRecord(human_author=human_author)

        # Principle flags (declared active per schema)
        self.principles = {
            "compliance_vs_correctness": True,
            "evidence_based_trust": True,
            "hierarchical_authority": True,
        }

    # ------------------------------------------------------------------
    # Schema loading / validation
    # ------------------------------------------------------------------
    def _load_schema(self) -> dict:
        try:
            with open(self.schema_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Schema file is descriptive; the engine enforces the rules in
            # code regardless of file presence.
            return {}

    def validate_record(self, record: dict) -> list[str]:
        """Validate a record dict against the governance schema.

        Returns a list of human-readable error messages (empty = valid).
        This is a best-effort structural check; the real enforcement happens
        in the mutating methods below.
        """
        errors: list[str] = []
        if not isinstance(record, dict):
            return ["record must be a JSON object"]

        # Top-level required keys
        for key in ("schema_version", "governance", "record"):
            if key not in record:
                errors.append(f"missing required top-level key: {key}")

        # Governance section
        gov = record.get("governance", {})
        if not isinstance(gov, dict):
            errors.append("governance must be an object")
        else:
            for pid in ("compliance_vs_correctness", "evidence_based_trust",
                        "hierarchical_authority"):
                found = any(p.get("principle_id") == pid
                            for p in gov.get("principles", []))
                if not found:
                    errors.append(f"governance.principles missing: {pid}")
            auth = gov.get("authority_model", {})
            if not auth.get("commander_is_sole_correctness_authority"):
                errors.append("authority_model.commander_is_sole_correctness_authority must be true")
            if not auth.get("ai_may_not_self_certify_correctness"):
                errors.append("authority_model.ai_may_not_self_certify_correctness must be true")

        # Record section
        rec = record.get("record", {})
        if not isinstance(rec, dict):
            errors.append("record must be an object")
        else:
            for key in ("claims", "sources", "actions", "attribution",
                        "evidence_reviews"):
                if key not in rec:
                    errors.append(f"record missing required key: {key}")

        # Attribution: ai_role must be supporting_tool
        attr = rec.get("attribution", {})
        if attr.get("ai_role") != AI_ROLE:
            errors.append(f"attribution.ai_role must be '{AI_ROLE}'")

        # AI must not self-certify correctness
        reasoning = rec.get("reasoning", {})
        if reasoning.get("ai_self_certified_correct") is True:
            errors.append("reasoning.ai_self_certified_correct must be false")

        # Evidence-based trust: every supported claim must have source_ids
        for claim in rec.get("claims", []):
            if not isinstance(claim, dict):
                errors.append("claim must be an object")
                continue
            if claim.get("support_status") == SupportStatus.SUPPORTED \
                    and not claim.get("source_ids"):
                errors.append(
                    f"claim {claim.get('claim_id')} is 'supported' but has no source_ids"
                )
            if claim.get("support_status") == SupportStatus.SUPPORTED \
                    and not claim.get("reasoning_steps"):
                errors.append(
                    f"claim {claim.get('claim_id')} is 'supported' but has no reasoning_steps"
                )

        return errors

    # ------------------------------------------------------------------
    # Principle 1: Compliance vs. Correctness
    # ------------------------------------------------------------------
    def draft_action(self, action_id: str, action_type: str,
                     summary: str, external_or_state_changing: bool = False,
                     target: str | None = None,
                     reversibility: str = "unknown") -> ActionRecord:
        """Create a draft action. Compliance and correctness start unassessed."""
        action = ActionRecord(
            action_id=action_id,
            action_type=action_type,
            external_or_state_changing=external_or_state_changing,
            compliance_status=ComplianceStatus.NOT_ASSESSED,
            correctness_status=CorrectnessStatus.NOT_ASSESSED,
            reversibility=reversibility,
        )
        self.actions[action_id] = action
        return action

    def grant_compliance(self, action_id: str, approver: str, scope: str,
                         reasoning: str = "") -> None:
        """Grant compliance (procedure followed) for an action.

        This satisfies the pre-action gate (approval, scope,
        prior-to-execution). It does NOT assert correctness.
        """
        if not self.principles["compliance_vs_correctness"]:
            raise GovernanceViolationError(
                "compliance_vs_correctness", "principle is inactive")
        action = self.actions.get(action_id)
        if action is None:
            raise GovernanceViolationError(
                "compliance_vs_correctness", f"unknown action {action_id}")
        action.compliance_status = ComplianceStatus.COMPLIANT
        action.compliance_reasoning = (
            f"Approved by {approver}; scope={scope}. {reasoning}".strip()
        )

    def record_compliance(self, action_id: str, compliant: bool,
                          reasoning: str = "") -> None:
        """Record a compliance assessment independently of correctness."""
        if not self.principles["compliance_vs_correctness"]:
            raise GovernanceViolationError(
                "compliance_vs_correctness", "principle is inactive")
        action = self.actions.get(action_id)
        if action is None:
            raise GovernanceViolationError(
                "compliance_vs_correctness", f"unknown action {action_id}")
        action.compliance_status = (
            ComplianceStatus.COMPLIANT if compliant
            else ComplianceStatus.NON_COMPLIANT
        )
        action.compliance_reasoning = reasoning

    def is_compliant(self, action_id: str) -> bool:
        action = self.actions.get(action_id)
        return bool(action and action.compliance_status == ComplianceStatus.COMPLIANT)

    # ------------------------------------------------------------------
    # Principle 3: Hierarchical Authority — Commander enforces correctness
    # ------------------------------------------------------------------
    def commander_review(self, review_id: str, reviewed_by: str,
                         target_id: str, target_type: str,
                         correctness: str, compliance: str = ComplianceStatus.NOT_ASSESSED,
                         reasoning: str = "", commander_override: bool = False,
                         notes: str | None = None) -> EvidenceReviewRecord:
        """Commander enforces correctness on a target (task/action/claim).

        Only the Commander may set correctness_status. The AI must never call
        this to self-certify. ``reviewed_by`` is the Commander identity.
        """
        if not self.principles["hierarchical_authority"]:
            raise GovernanceViolationError(
                "hierarchical_authority", "principle is inactive")
        if reviewed_by == "ai" or reviewed_by == "supporting_tool":
            raise GovernanceViolationError(
                "hierarchical_authority",
                "the AI may not review/enforce correctness; reviewed_by must be the Commander")

        review = EvidenceReviewRecord(
            review_id=review_id,
            reviewed_by=reviewed_by,
            reviewed_at=_utc_now(),
            target_id=target_id,
            target_type=target_type,
            compliance_assessment=compliance,
            correctness_assessment=correctness,
            reasoning=reasoning,
            commander_override=commander_override,
            notes=notes,
        )
        self.reviews[review_id] = review

        # Mirror onto action if applicable
        if target_type == "action":
            action = self.actions.get(target_id)
            if action:
                action.compliance_status = compliance
                action.correctness_status = correctness
                action.correctness_reasoning = reasoning
                action.commander_reviewed = True
                action.commander_reviewed_at = _utc_now()

        return review

    def is_correct(self, action_id: str) -> bool:
        action = self.actions.get(action_id)
        return bool(action and action.correctness_status == CorrectnessStatus.CORRECT)

    def commander_reviewed(self, action_id: str) -> bool:
        action = self.actions.get(action_id)
        return bool(action and action.commander_reviewed)

    # ------------------------------------------------------------------
    # Principle 2: Evidence-Based Trust
    # ------------------------------------------------------------------
    def add_source(self, source_id: str, title: str,
                   access_status: str = "not_checked",
                   source_category: str = "other",
                   author_or_publisher: str | None = None,
                   url: str | None = None) -> SourceRecord:
        source = SourceRecord(
            source_id=source_id,
            title=title,
            access_status=access_status,
            source_category=source_category,
            author_or_publisher=author_or_publisher,
            url=url,
        )
        self.sources[source_id] = source
        return source

    def add_claim(self, claim_id: str, text: str,
                  epistemic_status: str = EpistemicStatus.UNKNOWN,
                  source_ids: list[str] | None = None,
                  reasoning_steps: list[dict] | None = None,
                  uncertainty: str = "",
                  verification_criterion: str | None = None) -> ClaimRecord:
        """AI proposes a claim with evidence metadata.

        The AI sets epistemic_status, uncertainty, and lists sources/reasoning,
        but support_status starts as UNVERIFIED. The AI may not mark a claim
        as 'supported' without evidence.
        """
        if not self.principles["evidence_based_trust"]:
            raise GovernanceViolationError(
                "evidence_based_trust", "principle is inactive")

        claim = ClaimRecord(
            claim_id=claim_id,
            text=text,
            epistemic_status=epistemic_status,
            support_status=SupportStatus.UNVERIFIED,  # AI does not assert support
            source_ids=list(source_ids or []),
            reasoning_steps=list(reasoning_steps or []),
            uncertainty=uncertainty,
            verification_criterion=verification_criterion,
        )
        self.claims[claim_id] = claim
        return claim

    def ai_attempt_support(self, claim_id: str,
                           proposed_support: str) -> None:
        """AI attempts to assert support for a claim.

        Enforcement: a claim can only be marked SUPPORTED/PARTLY_SUPPORTED if
        it has source_ids AND reasoning_steps. Otherwise it remains UNVERIFIED
        and a GovernanceViolationError is raised if the AI tries to force it.
        """
        claim = self.claims.get(claim_id)
        if claim is None:
            raise GovernanceViolationError(
                "evidence_based_trust", f"unknown claim {claim_id}")

        has_sources = bool(claim.source_ids)
        has_reasoning = bool(claim.reasoning_steps)

        if proposed_support in (SupportStatus.SUPPORTED, SupportStatus.PARTLY_SUPPORTED):
            if not has_sources or not has_reasoning:
                raise GovernanceViolationError(
                    "evidence_based_trust",
                    f"claim {claim_id} cannot be '{proposed_support}' without "
                    f"source_ids and reasoning_steps (evidence-based trust)"
                )
            claim.support_status = proposed_support
        else:
            claim.support_status = proposed_support

    def claim_requires_evidence(self, claim_id: str) -> bool:
        """True if the claim is marked supported/partly_supported but lacks evidence."""
        claim = self.claims.get(claim_id)
        if claim is None:
            return False
        if claim.support_status in (SupportStatus.SUPPORTED,
                                    SupportStatus.PARTLY_SUPPORTED):
            return not (claim.source_ids and claim.reasoning_steps)
        return False

    # ------------------------------------------------------------------
    # AI subordinate boundary — AI may propose but not self-certify
    # ------------------------------------------------------------------
    def ai_propose_result(self, action_id: str, result: str,
                          uncertainty: str = "not_assessed") -> None:
        """AI proposes a result for an action.

        The AI reports the outcome with uncertainty but does NOT set
        correctness_status. Correctness remains NOT_ASSESSED until the
        Commander reviews.
        """
        if not self.principles["hierarchical_authority"]:
            raise GovernanceViolationError(
                "hierarchical_authority", "principle is inactive")
        action = self.actions.get(action_id)
        if action is None:
            raise GovernanceViolationError(
                "hierarchical_authority", f"unknown action {action_id}")
        # AI may record the proposal but must not touch correctness_status
        action.correctness_reasoning = (
            f"AI-proposed result: {result}. uncertainty={uncertainty}. "
            "Correctness pending Commander review."
        )

    def assert_ai_cannot_self_certify(self, action_id: str) -> None:
        """Explicitly assert that the AI has NOT certified correctness.

        Call this to document that correctness is pending Commander review.
        """
        action = self.actions.get(action_id)
        if action is None:
            raise GovernanceViolationError(
                "hierarchical_authority", f"unknown action {action_id}")
        if action.correctness_status != CorrectnessStatus.NOT_ASSESSED:
            raise GovernanceViolationError(
                "hierarchical_authority",
                f"action {action_id} correctness was set without Commander review")

    # ------------------------------------------------------------------
    # Record export (schema-aligned)
    # ------------------------------------------------------------------
    def to_record_dict(self) -> dict:
        return {
            "schema_version": "1.0.0",
            "governance": {
                "principles": [
                    {"principle_id": "compliance_vs_correctness",
                     "active": self.principles["compliance_vs_correctness"],
                     "description": "Compliance (procedure followed) is tracked separately from Correctness (evidence-supported result). Compliance does not imply correctness."},
                    {"principle_id": "evidence_based_trust",
                     "active": self.principles["evidence_based_trust"],
                     "description": "Every assertion must carry explicit evidence (source_ids) and step-by-step reasoning (reasoning_steps). Trust is derived from traceable logic, not probabilistic confidence."},
                    {"principle_id": "hierarchical_authority",
                     "active": self.principles["hierarchical_authority"],
                     "description": "The Commander is the sole authority for enforcing correctness. The AI is a subordinate executor and must never self-certify correctness."},
                ],
                "authority_model": {
                    "commander_is_sole_correctness_authority": True,
                    "ai_may_not_self_certify_correctness": True,
                    "ai_role": AI_ROLE,
                },
            },
            "record": {
                "claims": [c.to_dict() for c in self.claims.values()],
                "sources": [s.to_dict() for s in self.sources.values()],
                "actions": [a.to_dict() for a in self.actions.values()],
                "attribution": self.attribution.to_dict(),
                "evidence_reviews": [r.to_dict() for r in self.reviews.values()],
                "reasoning": {
                    "summary": "Governance-enforced record; AI does not self-certify correctness.",
                    "ai_self_certified_correct": False,
                },
            },
        }

    def validation_errors(self) -> list[str]:
        return self.validate_record(self.to_record_dict())
