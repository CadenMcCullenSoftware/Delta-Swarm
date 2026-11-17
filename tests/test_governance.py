"""Unit tests for the GovernanceEngine — enforcement of the three principles."""

import json
import pytest

from swarm.governance import (
    AI_ROLE,
    ComplianceStatus,
    CorrectnessStatus,
    EpistemicStatus,
    EvidenceReviewRecord,
    GovernanceEngine,
    GovernanceViolationError,
    SourceRecord,
    SupportStatus,
    _utc_now,
)


def test_engine_initializes_with_active_principles():
    engine = GovernanceEngine(human_author="Caden McCullen")
    assert engine.principles["compliance_vs_correctness"] is True
    assert engine.principles["evidence_based_trust"] is True
    assert engine.principles["hierarchical_authority"] is True
    assert engine.attribution.ai_role == AI_ROLE
    assert engine.attribution.human_author == "Caden McCullen"


# ---------------- Principle 1: Compliance vs. Correctness ----------------

def test_compliance_and_correctness_start_unassessed():
    engine = GovernanceEngine()
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    action = engine.actions["act-1"]
    assert action.compliance_status == ComplianceStatus.NOT_ASSESSED
    assert action.correctness_status == CorrectnessStatus.NOT_ASSESSED


def test_grant_compliance_sets_compliance_only_not_correctness():
    """Compliance does NOT imply correctness."""
    engine = GovernanceEngine()
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    engine.grant_compliance(
        action_id="act-1", approver="commander", scope="test",
        reasoning="approval granted",
    )
    action = engine.actions["act-1"]
    assert action.compliance_status == ComplianceStatus.COMPLIANT
    assert action.correctness_status == CorrectnessStatus.NOT_ASSESSED


def test_compliant_but_incorrect_is_possible():
    """A compliant action can still be incorrect — compliance != correctness."""
    engine = GovernanceEngine()
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    engine.grant_compliance(
        action_id="act-1", approver="commander", scope="test",
        reasoning="procedure followed",
    )
    # Commander marks it incorrect despite compliance
    engine.commander_review(
        review_id="r-1", reviewed_by="commander", target_id="act-1",
        target_type="action", correctness="incorrect",
        compliance="compliant", reasoning="result wrong despite procedure",
    )
    action = engine.actions["act-1"]
    assert action.compliance_status == ComplianceStatus.COMPLIANT
    assert action.correctness_status == CorrectnessStatus.INCORRECT


def test_incorrect_but_compliant_action_not_correct():
    engine = GovernanceEngine()
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    engine.commander_review(
        review_id="r-1", reviewed_by="commander", target_id="act-1",
        target_type="action", correctness="correct",
        compliance="non_compliant", reasoning="right result, wrong procedure",
    )
    action = engine.actions["act-1"]
    assert action.compliance_status == ComplianceStatus.NON_COMPLIANT
    assert action.correctness_status == CorrectnessStatus.CORRECT


# ---------------- Principle 2: Evidence-Based Trust ----------------

def test_ai_proposed_claim_starts_unverified():
    """AI may not self-certify support; claims start UNVERIFIED."""
    engine = GovernanceEngine()
    engine.add_claim(
        claim_id="c-1", text="The sky is blue",
        epistemic_status="direct_observation",
        source_ids=["s-1"],
        reasoning_steps=[{"step_id": "s1", "description": "observe sky",
                          "evidence_ids": ["s-1"], "conclusion": "blue",
                          "uncertainty": "low"}],
    )
    claim = engine.claims["c-1"]
    assert claim.support_status == SupportStatus.UNVERIFIED


def test_claim_cannot_be_supported_without_evidence():
    """Evidence-based trust: supported requires source_ids AND reasoning_steps."""
    engine = GovernanceEngine()
    engine.add_claim(
        claim_id="c-1", text="The sky is blue",
        epistemic_status="direct_observation",
        source_ids=[], reasoning_steps=[],
    )
    with pytest.raises(GovernanceViolationError) as exc:
        engine.ai_attempt_support("c-1", SupportStatus.SUPPORTED)
    assert "evidence-based trust" in str(exc.value).lower()
    # Claim remains unverified
    assert engine.claims["c-1"].support_status == SupportStatus.UNVERIFIED


def test_claim_can_be_supported_with_sources_and_reasoning():
    engine = GovernanceEngine()
    engine.add_claim(
        claim_id="c-1", text="The sky is blue",
        epistemic_status="direct_observation",
        source_ids=["s-1"],
        reasoning_steps=[{"step_id": "s1", "description": "observe sky",
                          "evidence_ids": ["s-1"], "conclusion": "blue",
                          "uncertainty": "low"}],
    )
    engine.ai_attempt_support("c-1", SupportStatus.SUPPORTED)
    assert engine.claims["c-1"].support_status == SupportStatus.SUPPORTED


def test_claim_requires_evidence_detects_unsupported_claim():
    engine = GovernanceEngine()
    engine.add_claim(
        claim_id="c-1", text="unsupported claim",
        epistemic_status="opinion_or_recommendation",
        source_ids=[], reasoning_steps=[],
    )
    # Manually mark supported to simulate AI overreach attempt
    engine.claims["c-1"].support_status = SupportStatus.SUPPORTED
    assert engine.claim_requires_evidence("c-1") is True


def test_add_source_records_metadata():
    engine = GovernanceEngine()
    engine.add_source(
        source_id="s-1", title="NIST AI RMF",
        access_status="opened_and_reviewed",
        source_category="government_publication",
    )
    source = engine.sources["s-1"]
    assert source.title == "NIST AI RMF"
    assert source.access_status == "opened_and_reviewed"


# ---------------- Principle 3: Hierarchical Authority ----------------

def test_ai_cannot_self_certify_correctness():
    """The AI (reviewed_by='ai') may not enforce correctness."""
    engine = GovernanceEngine()
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    with pytest.raises(GovernanceViolationError) as exc:
        engine.commander_review(
            review_id="r-1", reviewed_by="ai", target_id="act-1",
            target_type="action", correctness="correct",
            compliance="compliant", reasoning="ai says so",
        )
    assert "may not review/enforce correctness" in str(exc.value)
    # Correctness remains unassessed
    assert engine.actions["act-1"].correctness_status == CorrectnessStatus.NOT_ASSESSED


def test_commander_can_enforce_correctness():
    engine = GovernanceEngine()
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    review = engine.commander_review(
        review_id="r-1", reviewed_by="Caden McCullen", target_id="act-1",
        target_type="action", correctness="correct",
        compliance="compliant", reasoning="evidence verified",
    )
    assert review.reviewed_by == "Caden McCullen"
    assert review.correctness_assessment == CorrectnessStatus.CORRECT
    action = engine.actions["act-1"]
    assert action.correctness_status == CorrectnessStatus.CORRECT
    assert action.commander_reviewed is True


def test_ai_propose_result_does_not_self_certify():
    """AI may propose a result but must not set correctness."""
    engine = GovernanceEngine()
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    engine.ai_propose_result(
        action_id="act-1", result="output", uncertainty="not_assessed",
    )
    action = engine.actions["act-1"]
    assert action.correctness_status == CorrectnessStatus.NOT_ASSESSED
    assert "Correctness pending Commander review" in action.correctness_reasoning


def test_assert_ai_cannot_self_certify_passes_when_unassessed():
    engine = GovernanceEngine()
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    # Should not raise: correctness is NOT_ASSESSED (AI hasn't touched it)
    engine.assert_ai_cannot_self_certify("act-1")


def test_assert_ai_cannot_self_certify_raises_if_correctness_set():
    engine = GovernanceEngine()
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    engine.commander_review(
        review_id="r-1", reviewed_by="commander", target_id="act-1",
        target_type="action", correctness="correct",
        compliance="compliant", reasoning="ok",
    )
    # Once correctness is set, we can no longer confirm the AI didn't touch it
    with pytest.raises(GovernanceViolationError):
        engine.assert_ai_cannot_self_certify("act-1")


# ---------------- Record export & validation ----------------

def test_to_record_dict_is_schema_aligned():
    engine = GovernanceEngine(human_author="Caden McCullen")
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    engine.add_source("s-1", "Source", access_status="opened_and_reviewed")
    engine.add_claim("c-1", "claim", epistemic_status="direct_observation",
                     source_ids=["s-1"],
                     reasoning_steps=[{"step_id": "s1", "description": "d",
                                       "evidence_ids": ["s-1"],
                                       "conclusion": "c", "uncertainty": "l"}])
    record = engine.to_record_dict()
    assert record["schema_version"] == "1.0.0"
    assert record["governance"]["authority_model"][
        "commander_is_sole_correctness_authority"] is True
    assert record["governance"]["authority_model"][
        "ai_may_not_self_certify_correctness"] is True
    assert record["governance"]["authority_model"]["ai_role"] == AI_ROLE
    assert record["record"]["attribution"]["ai_role"] == AI_ROLE
    assert record["record"]["reasoning"]["ai_self_certified_correct"] is False
    assert len(record["record"]["sources"]) == 1
    assert len(record["record"]["claims"]) == 1
    assert len(record["record"]["actions"]) == 1


def test_validation_errors_empty_when_valid():
    engine = GovernanceEngine(human_author="Caden McCullen")
    engine.draft_action("act-1", "other", "test", external_or_state_changing=True)
    engine.add_source("s-1", "Source", access_status="opened_and_reviewed")
    engine.add_claim("c-1", "claim", epistemic_status="direct_observation",
                     source_ids=["s-1"],
                     reasoning_steps=[{"step_id": "s1", "description": "d",
                                       "evidence_ids": ["s-1"],
                                       "conclusion": "c", "uncertainty": "l"}])
    assert engine.validation_errors() == []


def test_validation_errors_flag_unsupported_claim_without_sources():
    engine = GovernanceEngine()
    engine.add_claim("c-1", "claim", epistemic_status="direct_observation",
                     source_ids=[], reasoning_steps=[])
    engine.claims["c-1"].support_status = SupportStatus.SUPPORTED
    errors = engine.validation_errors()
    assert any("source_ids" in e for e in errors)


def test_utc_now_returns_iso_string():
    ts = _utc_now()
    assert "T" in ts
    assert "+" in ts or ts.endswith("Z")
