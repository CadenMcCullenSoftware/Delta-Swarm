# Swarm

Multi-agent swarm system for user-controlled workflow execution.

## Overview

Swarm is a local multi-agent orchestrator that runs workflow tasks across
cooperating agents. Every state-changing action passes through an explicit
pre-action approval gate, and all claims, sources, artifacts, and actions are
recorded in a structured evidence record aligned with the agent-design schema.

## Principles

- **User control:** agents prepare plans and execute tasks; named humans retain
  approval and deployment decisions. Preview, review, and authorization are
  distinct actions.
- **Automation gating:** state-changing actions require explicit, prior approval
  before execution. The gate covers approval, scope confirmation, reversibility,
  and post-run verification.
- **Evidence grounding:** every claim carries epistemic and support metadata;
  every source carries access status and limitations.
- **Attribution:** the AI is framed as a supporting tool, not an autonomous
  decision-maker. Human authorship is recorded explicitly.
- **Compliance vs. correctness:** procedure-compliant or syntactically valid
  output is not proof that the result is correct.
- **Evidence-based trust:** claims require traceable evidence, primary sources
  when available, and explicit reasoning; agreement or self-critique alone is
  not independent verification.
- **Commander authority:** the human commander is the final authority for
  correctness and operational authorization. The AI may analyze and propose,
  but does not self-certify correctness or authorize state-changing actions.

## Installation

```bash
python -m pip install -e '.[dev]'
```

## Quick start

```python
from swarm.swarm import Swarm
from swarm.types import Task

swarm = Swarm.default_swarm(name="release")
swarm.add_task(Task(
    task_id="hello",
    name="hello",
    command=["python", "-c", "print('hello')"],
))
print(swarm.run())
```

## Command reference

- `swarm add --workflow <name> --task-id <id> --name <name> --command <cmd>...`
  - Adds a task to a workflow. `--depends-on` lists prerequisite task ids.
  - `--requires-approval` marks the task as needing explicit approval before execution.
- `swarm run --workflow <name> [--coordinator <id>] [--auto-approve]`
  - Executes tasks in dependency order. Tasks requiring approval block until approved.
- `swarm approve --action-id <id>`
  - Approves a pending state-changing action and unblocks its task.
- `swarm decline --action-id <id>`
  - Declines a pending action and cancels its task.
- `swarm status --workflow <name>`
  - Prints the swarm summary as JSON (agents, tasks, actions, evidence record).
- `swarm governance-check --claim-id <id> --text <text> [--syntax-valid] [--instruction-followed] [--causally-sound] [--primary-source <id>...]`
  - Runs the AI evidence pre-check without self-certifying correctness.
- `swarm governance-load --config <path>`
  - Validates a lightweight agent governance configuration.

Workflow and evidence state is in memory. Each separate CLI invocation creates
a new swarm, so `add` followed by `run`, or `run` followed by `approve` or
`status`, does not share state. Use the Python API in one process or the `swarm
nlp` REPL for a multi-step workflow. Persistent CLI state is not included.

## Natural-language (NLP) mode

For easier, sentence-style command entry, use the interactive `nlp` mode:

```bash
swarm nlp
```

Examples (type at the `swarm>` prompt):

```text
add task build command echo hello
add task test command pytest depends on build approval
run workflow release auto-approve
approve action action-test
decline action action-deploy
status workflow release
help
exit
```

The parser recognizes `add/create/new`, `run/start/execute`, `approve/authorize`, `decline/reject`, and `status/show/list`, plus `task`, `workflow`, `command`, `depends on`, and `approval` keywords.

## Architecture

- `swarm.agent` — base `Agent` and role-specific agents (planner, worker, reviewer, coordinator).
- `swarm.message_bus` — in-memory publish-subscribe bus for agent communication.
- `swarm.workflow` — task graph with dependency ordering and readiness checks.
- `swarm.gate` — pre-action approval gate for state-changing operations.
- `swarm.record` — structured evidence record (claims, sources, artifacts, actions, attribution).
- `swarm.swarm` — `Swarm` coordinator orchestrating agents across workflows.
- `swarm.cli` — command-line interface.

## Testing

```bash
python -m pytest tests/ -v
```

## License

MIT

## Detailed documentation

See [docs/swarm.md](./docs/swarm.md) for full module reference, CLI/NLP reference, evidence-record schema, automation-gating checklist, sandboxing/security analysis with research sources, usage examples, testing status, and known limitations.

See [docs/governance/](./docs/governance/) for governance documents: system philosophy summary, communication protocol, pre-action gating checklist, source verification procedure, disagreement-handling playbook, evidence review step, safety impact assessment, authorship and credit rules, research-to-outcome workflow, and alignment checkpoint form. See [docs/terminology_glossary.md](./docs/terminology_glossary.md) for the standardized terminology glossary.

See [docs/handoff/](./docs/handoff/) for the pilot overview, quickstart and
verification steps, draft offer sheet, and acceptance checklist.
