# Terminology Glossary

Standardized terminology used across the swarm system. This glossary maps
legacy or variant terms to the canonical term used in code, configuration,
and documentation.

## Principle: Compliance does not equal Correctness

| Concept | Canonical term | Variant / legacy term | Notes |
|---------|---------------|----------------------|-------|
| Compliance status | `compliance_status` | — | Procedure followed (approval, scope, prior-to-execution) |
| Correctness status | `correctness_status` | — | Evidence-supported result; commander-enforced |
| Compliance value | `compliant` | — | Procedure was followed |
| Non-compliance value | `non_compliant` | — | Procedure was not followed |
| Correct value | `correct` | — | Result is evidence-supported |
| Incorrect value | `incorrect` | — | Result is not evidence-supported |
| Uncertain value | `uncertain` | — | Evidence is insufficient to determine |
| Not assessed value | `not_assessed` | — | No evaluation performed yet |

**Rule:** Compliance (`compliant`) does not imply correctness (`correct`).
A task can be `compliant` but `incorrect`.

## Principle: Evidence-Based Trust

| Concept | Canonical term | Variant / legacy term | Notes |
|---------|---------------|----------------------|-------|
| Epistemic status | `epistemic_status` | — | Nature of knowledge (source_reported_fact, direct_observation, etc.) |
| Support status | `support_status` | — | Degree of evidentiary support (supported, unverified, etc.) |
| Source identifier | `source_id` | — | Unique reference to an evidence source |
| Reasoning steps | `reasoning_steps` | — | Step-by-step traceable logic |
| Verification criterion | `verification_criterion` | — | Standard used to verify a claim |
| Uncertainty | `uncertainty` | — | Explicit disclosure of confidence limits |
| Limitations | `limitations` | — | Known constraints on a claim or source |
| AI self-certification | `ai_self_certified_correct` | — | Always `false`; AI never certifies correctness |

**Rule:** Trust requires traceable evidence and reasoning. Self-critique,
agreement, or confidence are not independent verification.

## Principle: Commander Authority

| Concept | Canonical term | Variant / legacy term | Notes |
|---------|---------------|----------------------|-------|
| AI role | `supporting_tool` | `SUPPORTIVE_TOOL` | The AI is a supportive analytical instrument |
| Commander | `commander` / `human_commander` | `HUMAN_COMMANDER` | Human with final authority over correctness |
| Reviewed by | `reviewed_by` | — | Identity of the commander performing review |
| Commander reviewed | `commander_reviewed` | — | Boolean flag indicating commander review |
| Commander override | `commander_override` | — | Flag for commander overriding AI assessment |
| Human author | `human_author` | — | Attributed human author of the work |
| Attribution basis | `attribution_basis` | — | Basis for human authorship attribution |

**Rule:** The AI is a supporting tool, never an autonomous decision-maker.
Correctness and execution authorization rest solely with the human commander.

## Action and Workflow Terminology

| Concept | Canonical term | Variant / legacy term | Notes |
|---------|---------------|----------------------|-------|
| Action | `action` | — | State-changing or read-only operation |
| Task | `task` | — | Unit of work in a workflow |
| Workflow | `workflow` | — | Directed graph of tasks with dependencies |
| Approval gate | `approval_gate` | — | Pre-action compliance checkpoint |
| Reversibility | `reversibility` | — | Degree to which an action can be undone |
| External or state-changing | `external_or_state_changing` | — | Flag for actions that modify state |
| Evidence review | `evidence_review` | — | Commander's formal review record |

## Configuration Terminology (agent_governance_schema.json)

| Concept | Canonical term | Variant / legacy term | Notes |
|---------|---------------|----------------------|-------|
| Compliance equals correctness | `compliance_equals_correctness` | — | Must be `false` |
| Trust foundation | `trust_foundation` | — | `primary_evidence` or `empirical_reasoning` |
| Independent verification | `require_independent_verification` | — | Must be `true` |
| Commander approval required | `commander_approval_required` | — | Must be `true` |

## Files and Modules

| File | Role |
|------|------|
| `src/swarm/types.py` | Core type definitions (enums, dataclasses) |
| `src/swarm/gate.py` | Pre-action approval gate |
| `src/swarm/governance.py` | Governance engine (runtime enforcement) |
| `src/swarm/agent_logic.py` | Agent logic enforcer (middleware) |
| `src/swarm/record.py` | Evidence record keeping |
| `src/swarm/swarm.py` | Swarm coordinator |
| `src/swarm/agent.py` | Base agent and role implementations |
| `src/swarm/message_bus.py` | In-memory publish-subscribe bus |
| `src/swarm/workflow.py` | Task graph and dependency ordering |
| `src/swarm/cli.py` | Command-line interface |
| `docs/governance.schema.json` | Formal governance JSON schema (draft-07) |
| `docs/agent_governance_schema.json` | Lightweight agent governance config |

## Changes Applied

| Area | Old term | New term | File |
|------|----------|----------|------|
| AI role enum | `SUPPORTIVE_TOOL` | `supporting_tool` | `docs/agent_governance_schema.json` |
| Commander role enum | `HUMAN_COMMANDER` | `human_commander` | `docs/agent_governance_schema.json` |
