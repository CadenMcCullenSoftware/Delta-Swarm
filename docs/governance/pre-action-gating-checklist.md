# Pre-Action Gating Checklist

Required for any automation (changes to system state, code execution, or
sending communications). All four elements must be satisfied before an
operational action occurs.

## 1. Approval

Explicit user confirmation is required before the action is executed or added
to a workflow. The human operator retains authority over whether the action
occurs. The AI may help plan or analyze, but the human decides.

## 2. Scope Confirmation

The gate records the approved scope (target and boundaries of the action) and
confirms that the action is limited to that scope. The commander reviews and
confirms the scope before execution.

## 3. Rollback Plan

Reversibility is recorded per action (`reversible`, `partly_reversible`,
`irreversible`, or `unknown`). Operators define a rollback plan for each
state-changing action before approval. Irreversible actions require additional
commander scrutiny.

## 4. Post-Run Verification

Task results and errors are recorded after execution. The commander reviews
correctness separately from compliance. Correctness remains `not_assessed`
until the human commander reviews. The AI does not self-certify correctness.

## Checklist Flow

1. AI drafts the action with summary, target, inputs, effects, side effects,
   and reversibility.
2. Gate requests approval from the commander (required, explicit,
   prior-to-execution).
3. Commander reviews scope and approves or declines.
4. If approved, the action executes; results and errors are recorded.
5. Commander reviews correctness (correct / incorrect / uncertain).

## Gating Rule

A successful test or generated plan is not itself authorization; a separate
explicit approval step is required.
