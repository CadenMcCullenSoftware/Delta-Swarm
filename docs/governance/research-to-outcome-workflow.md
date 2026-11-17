# Research-to-Outcome Workflow

A workflow for tool-assisted research with checkpoints, logging, synthesis, and
final deliverable criteria.

## Phase 1: Review Plan

Before research begins, create a review plan defining:
- Relevant terms and topics
- Guiding questions
- Scope
- Evidence standards

## Phase 2: Research Checkpoints

Conduct research with periodic checkpoints:
- Inventory relevant files, modules, interface text, documentation, comments,
  variable and function names, and configuration files
- Verify external tools, libraries, APIs, links, scripts, files, and packages
  against primary sources and explicit evidence
- Log all sources consulted, including access status and limitations

## Phase 3: Logging

Maintain a research log recording:
- Sources consulted (title, author, URL, access date, access status)
- Claims extracted from each source (epistemic status, support status)
- Reasoning steps connecting evidence to conclusions
- Uncertainties and limitations identified

## Phase 4: Synthesis

Synthesize findings into conclusions:
- Each conclusion has supporting data or links when available
- Claims that remain unverified are flagged as needing validation
- Facts, inferences, opinions, and unknowns are kept distinct
- Unsupported claims are not presented as established facts

## Phase 5: Final Deliverable Criteria

A final deliverable is complete when:
- All conclusions are traceable to evidence
- All claims have appropriate support status (supported, unverified, etc.)
- All sources have been verified for existence and applicability
- The attribution record credits Caden McCullen as human author
- The AI role is recorded as `supporting_tool`
- Governance validation passes (no `ai_self_certified_correct: true`)

## Output

A structured record containing claims, sources, reasoning, evaluation, and
attribution, aligned with the governance schema.
