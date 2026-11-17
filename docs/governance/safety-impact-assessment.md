# Safety Impact Assessment

Added to each workflow to ensure learning and growth without environmental or
operational damage.

## Purpose

Assess whether a workflow, task, or action could cause environmental harm,
operational damage, or safety incidents before execution.

## When to Apply

Before any state-changing action, code execution, or automation that could
affect the host system, network, or data.

## Assessment Items

| Item | Question | Response |
|------|----------|----------|
| State change | Does the action modify system state? | yes / no |
| Network egress | Does the action make outbound network connections? | yes / no |
| File system | Does the action read or write files outside a controlled directory? | yes / no |
| Privilege | Does the action require elevated privileges? | yes / no |
| Secrets | Does the action access or expose secrets or keys? | yes / no |
| Sandbox | Will the action run in a container or microVM? | yes / no |
| Reversibility | Is the action reversible if it causes damage? | reversible / partly_reversible / irreversible / unknown |

## Risk Mitigation

- Run untrusted or model-generated commands in a container or microVM, not
  directly on the host.
- Use `cwd` to restrict the working directory.
- Use `timeout` to bound execution wall-clock time.
- Pass commands as a list (not `shell=True`) to avoid shell injection.
- Do not expose or log secrets and keys.
- Do not commit secrets or keys to the repository.

## Decision

If any high-risk item is identified (network egress, file system access outside
controlled directory, privilege escalation, secrets exposure, irreversible
action without sandbox), the action requires additional commander review and
may be blocked.

## Record

The safety assessment is recorded as part of the action record, including
`reversibility`, `effects`, and `side_effects`.
