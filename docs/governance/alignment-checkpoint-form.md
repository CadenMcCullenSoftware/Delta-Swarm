# Alignment Checkpoint Form

Completed between phases to verify alignment with governance principles.

## Checkpoint Fields

| Field | Description | Value |
|-------|-------------|-------|
| Checkpoint ID | Unique identifier | |
| Phase | Current phase (review plan / research / synthesis / deliverable) | |
| Date | Checkpoint date | |
| Reviewed by | Commander identity | |

## Control

- [ ] Human commander retains authority over correctness and execution
- [ ] AI is framed as a supporting tool, not an autonomous decision-maker
- [ ] No unrequested actions proposed or executed

## Automation Approval

- [ ] Pre-action gating checklist completed (approval, scope, rollback,
  post-run verification)
- [ ] Explicit commander approval obtained for state-changing actions
- [ ] Compliance tracked separately from correctness

## Script Validation

- [ ] External tools, libraries, and APIs verified against primary sources
- [ ] Cited sources include applicable, runnable scripts
- [ ] Scripts executable in a controlled environment (sandbox / container /
  microVM)
- [ ] No secrets or keys exposed or logged

## Evidence

- [ ] Each conclusion has supporting data or links
- [ ] Claims carry epistemic status and support status
- [ ] Unverified claims flagged as needing validation
- [ ] Facts, inferences, opinions, and unknowns kept distinct

## Safety

- [ ] Safety impact assessment completed for state-changing actions
- [ ] Reversibility recorded per action
- [ ] Untrusted commands run in container or microVM, not on host

## Credit

- [ ] Human authorship attributed to Caden McCullen
- [ ] AI role recorded as `supporting_tool`
- [ ] Attribution preserved through credits, headers, and Git history

## Sign-off

Commander signature: ____________________  Date: __________

## Result

- [ ] Alignment confirmed — proceed to next phase
- [ ] Alignment not confirmed — remediate and re-check
