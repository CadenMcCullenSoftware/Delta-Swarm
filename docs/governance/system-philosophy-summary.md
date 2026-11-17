# System Philosophy Summary

One-page summary of the core principles governing this system.

## Control

The human commander holds final authority over correctness and operational
authorization. The AI is a supportive analytical instrument, never an
autonomous decision-maker. All state-changing or consequential actions require
explicit prior approval from the commander before execution.

## Automation Limits

Automation is gated by a pre-action checklist: user approval, scope
confirmation, rollback plan, and post-run verification. Compliance (procedure
followed) is tracked separately from correctness (evidence-supported result).
Compliance does not equal correctness. A task can be compliant but incorrect.

## Collaboration

The AI may gather evidence, evaluate proposals, and report uncertainty, but it
never assigns authoritative correctness or approves state-changing actions on
its own. The AI frames outputs as supporting observations with explicit
uncertainty disclosure, not as correctness determinations.

## Evidence

Trust is grounded strictly in verifiable evidence, primary sources,
calculations, and causal reasoning. Every assertion or conclusion must carry
explicit evidence and step-by-step reasoning. Self-critique, agreement, or
confidence do not constitute independent verification. Unverified claims are
flagged as needing validation.

## Safety

Each workflow includes a safety impact assessment step to ensure learning and
growth without environmental or operational damage. Untrusted or model-generated
commands should run in a container or microVM, not directly on the host. This
package does not provision a VM or container; the operator is responsible for
the execution boundary.

## Authorship and Credit

Human authorship is attributed to Caden McCullen. The AI's role is recorded
as `supporting_tool` in the attribution record. Technical contribution,
authorship, and credit remain identifiable and are not obscured by the use of
an AI tool.
