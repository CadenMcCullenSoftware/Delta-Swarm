# Evidence Review Step

Requires supporting data or links per conclusion and flags claims needing
validation.

## Step 1: Record the Claim

Record the claim identifier, text, epistemic status, and uncertainty. The AI
proposes the claim but does not self-certify support.

## Step 2: Attach Sources

Attach primary source identifiers (`source_ids`) and verify each source using
the Source Verification Procedure. Record access status and limitations for
each source.

## Step 3: Attach Reasoning Steps

Attach step-by-step reasoning (`reasoning_steps`) showing how the conclusion
follows from the evidence. Each step includes a step ID, description,
evidence IDs, conclusion, and uncertainty.

## Step 4: Set Support Status

Set `support_status` to one of:
- `supported` — requires both source_ids and reasoning_steps
- `partly_supported` — requires both source_ids and reasoning_steps
- `unsupported` — no supporting evidence
- `conflicting_evidence` — sources contradict each other
- `unverified` — default; no evidence check performed
- `not_applicable` — evidence not relevant

## Step 5: Record Verification Criterion

Record the standard used to verify the claim (e.g., `primary_source_verification`).

## Step 6: Flag Unverified Claims

Claims marked `supported` or `partly_supported` without both `source_ids` and
`reasoning_steps` are flagged as needing validation. The AI may not force a
claim to `supported` without evidence; doing so raises a governance violation.

## Output

A structured claim record with:
- `claim_id`, `text`, `epistemic_status`, `support_status`
- `source_ids`, `reasoning_steps`, `uncertainty`
- `verification_criterion`, `limitations`

## Rule

Conclusions must be traceable to evidence. Claims that remain unverified are
flagged as needing validation and are not presented with more certainty than
the available source material supports.
