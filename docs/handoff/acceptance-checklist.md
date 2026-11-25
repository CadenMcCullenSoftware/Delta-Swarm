# Pilot Acceptance Checklist

Complete this checklist for each delivery. Record the repository tag and full
commit hash so the verified source is identifiable.

## Before work begins

- [ ] Buyer, provider, fee, schedule, and scope are written down.
- [ ] Repository access and base license terms are confirmed.
- [ ] Custom-work ownership or license terms are in the signed statement of
  work.
- [ ] A named human commander approves the workflow, commands, target
  environment, permissions, and acceptance checks.
- [ ] Buyer acknowledges that commands run with the invoking user's host
  privileges and that the package has no sandbox or persistent storage.

## Independent setup and verification

- [ ] Clone or unpack the agreed tag; record tag and full commit hash.
- [ ] Record Python and operating-system versions.
- [ ] Install using `python -m pip install -e '.[dev]'`.
- [ ] Run `python -m py_compile src/swarm/*.py` successfully.
- [ ] Run `python -m pytest tests/ -v`; record the complete result.
- [ ] Parse both JSON schemas and the example configuration with
  `python -m json.tool`.
- [ ] Run `swarm governance-load --config docs/agent_governance_config.example.json`.
- [ ] Run `swarm validate` and `swarm --help`. Note that `validate` checks a
  fresh default record; separate CLI invocations do not share state.
- [ ] Run an agreed smoke workflow through the Python API in one process and
  record its output and status.
- [ ] Inspect the delivered source for local secrets and unrelated editor or
  build artifacts.

## Closeout

- [ ] Deliver the source and complete history through the agreed access method.
- [ ] Provide the verification record, included documentation, and known
  limitations.
- [ ] Human commander reviews the results and records acceptance or specific
  issues.
- [ ] Any work beyond the agreed scope is captured as a separately approved
  change before it starts.

**Buyer:** `[name]`  
**Human commander:** `[name]`  
**Tag / commit:** `[tag]` / `[full hash]`  
**Decision:** `[accepted / issues listed]`  
**Date:** `[date]`
