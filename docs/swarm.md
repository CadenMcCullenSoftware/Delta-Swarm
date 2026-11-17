# Swarm — Multi-Agent Workflow System

Detailed technical documentation for the multi-agent swarm system.

## 1. Overview

Swarm is a local multi-agent orchestrator that runs workflow tasks across
cooperating agents. Every state-changing action passes through an explicit
pre-action approval gate, and all claims, sources, artifacts, and actions are
recorded in a structured evidence record aligned with the agent-design schema
from `/home/kaden/Desktop/Agent-Docs/design.md`.

## 2. Architecture

### Core Principle: Compliance does not equal Correctness

The swarm enforces a hard separation between **compliance** and **correctness**:

| Concept | Meaning | Enforced by |
|---------|---------|-------------|
| **Compliance** | The procedure was followed: approval obtained, scope confirmed, prior-to-execution respected | The approval gate (`swarm approve`) |
| **Correctness** | The result is evidence-supported | The human **commander** (`swarm review-task` / `review-action`) |

- Approving an action means the pre-action gate was satisfied. It does **not** mean the result is correct.
- Correctness remains `CorrectnessStatus.NOT_ASSESSED` until the human commander reviews.
- The AI **never self-certifies correctness** (`ai_self_certified_correct` is always `false`). The AI is a supporting tool, not the commander.
- A task can be `compliant` (procedure followed) but `incorrect` (result wrong). Compliance does not equal correctness.
- **Evidence-based trust** — trust requires traceable sources and step-by-step reasoning. Syntactic compliance, agreement, confidence, or the AI's own self-critique is not independent verification.
- **Commander authority** — the human commander alone enforces correctness and final operational authorization. The AI may gather evidence, evaluate a proposal, and report uncertainty, but it never assigns authoritative correctness or approves a state-changing action on its own.

### 2.1 Core components

| Module | Responsibility |
|--------|--------------|
| `swarm/types.py` | Data models: agents, tasks, messages, actions, claims, sources, artifacts, attribution, evidence record, `ComplianceStatus`, `CorrectnessStatus`, `EvidenceReview` |
| `swarm/message_bus.py` | In-memory publish-subscribe blackboard for agent-to-agent communication |
| `swarm/workflow.py` | Task graph with dependency ordering (topological sort), readiness checks, status transitions |
| `swarm/gate.py` | Pre-action approval gate; tracks compliance separately from correctness |
| `swarm/agent.py` | Base `Agent` and roles: Planner, Worker, Reviewer, Coordinator. Agents report uncertainty; never self-certify correctness. |
| `swarm/swarm.py` | `Swarm` coordinator: orchestrates agents, runs workflows, manages approval, exposes `commander_review_task` / `commander_review_action` |
| `swarm/cli.py` | Command-line interface: `add`, `run`, `approve`, `decline`, `review-task`, `review-action`, `status`, `nlp` |

### 2.2 Data flow

1. A user adds tasks to a `Workflow`. Each task has a name, command (as an argument list), optional dependencies, timeout, failure-handling policy, and an approval flag.
2. The `Swarm.run()` method computes a topological dependency order and executes each task once its dependencies are complete.
3. Task execution selects a capable agent (planner/worker/reviewer/coordinator), marks the task `in_progress`, runs the command via `subprocess.run`, and marks the task `completed` or `failed`.
4. If a task requires approval, it is marked `blocked` at the gate until a human calls `approve_action` (or `swarm approve --action-id <id>`). Approval sets `compliance=compliant`; `correctness` stays `not_assessed`.
5. The human commander reviews the result via `commander_review_task` / `swarm review-task` and sets `correctness` (`correct`/`incorrect`/`uncertain`). The AI does not self-certify.
6. Every task and action is recorded in the `EvidenceRecord`, which carries claims, sources, artifacts, actions, reasoning, evaluation, attribution, and evidence reviews separating compliance from correctness.

### 2.3 Execution model

- Tasks run as child processes via `subprocess.run`, passing the command as a list (not through `shell=True`), which avoids shell-injection.
- `cwd`, `timeout`, stdout/stderr capture, and return-code handling are supported.
- Commands run with the invoking user's privileges on the host. There is **no** container, VM, or sandbox boundary in the current implementation (see Section 6).

## 3. Module reference

### 3.1 `swarm/types.py`

Defines all shared dataclasses and enums:

- `AgentRole`: `planner`, `worker`, `reviewer`, `coordinator`
- `TaskStatus`: `pending`, `assigned`, `in_progress`, `completed`, `failed`, `blocked`, `cancelled`
- `ActionType`: `draft_only`, `read_only`, `external_message`, `publish`, `purchase`, `delete`, `submit`, `access_change`, `data_disclosure`, `other`
- `ApprovalStatus`: `not_started`, `drafted`, `awaiting_approval`, `approved`, `declined`, `completed`, `blocked`
- `ComplianceStatus`: `compliant`, `non_compliant`, `not_assessed` — procedure followed
- `CorrectnessStatus`: `correct`, `incorrect`, `uncertain`, `not_assessed` — evidence-supported (commander-enforced)
- `Reversibility`: `reversible`, `partly_reversible`, `irreversible`, `unknown`
- `EpistemicStatus` / `SupportStatus`: evidence metadata per the agent-design schema
- `AgentRecord`, `Task`, `Message`, `ApprovalGate`, `Action`, `Claim`, `Source`, `Artifact`, `Reasoning`, `Evaluation`, `Attribution`, `EvidenceReview`, `SwarmRecord`

### 3.2 `swarm/message_bus.py`

`MessageBus` implements a publish-subscribe blackboard:
- `publish(from_agent, content, to_agent=None, reply_to=None)` — broadcasts to all subscribers if `to_agent` is `None`, otherwise to the named agent's handlers.
- `subscribe(agent_id, handler)` — registers a message handler for an agent.
- `messages_for(agent_id)` / `all_messages()` — query helpers.

### 3.3 `swarm/workflow.py`

`Workflow` manages a named collection of `Task` objects:
- `add_task(task)` — registers a task and invalidates the cached order.
- `dependency_order()` — returns task IDs in topological order; raises `ValueError` on circular dependencies or missing dependencies.
- `ready_tasks()` — returns pending tasks whose dependencies are all `completed`.
- `mark(task_id, status, ...)` — transitions a task's status and records result/error/assignment.

### 3.4 `swarm/gate.py`

`ApprovalGate` governs state-changing actions:
- `draft(...)` — creates an `Action` with metadata (summary, target, inputs, effects, reversibility).
- `request_approval(action_id, approver, scope)` — sets `required`, `explicit`, `prior_to_execution` to `true`, records approver/scope, and sets status to `awaiting_approval`.
- `approve(action_id)` / `decline(action_id)` — transitions status to `approved`/`declined`; raises `ValueError` if not awaiting approval.
- `mark_completed(action_id)` — requires `approved` status for state-changing actions; raises `ValueError` otherwise.
- `is_approved(action_id)` — returns `True` for non-state-changing actions or `approved` state-changing actions.

Conditional rule (from `design.md`): if `external_or_state_changing` is `true` and status is `approved`/`completed`, then `approval.required`, `approval.explicit`, and `approval.prior_to_execution` must all be `true`.

### 3.5 `swarm/agent.py`

Base `Agent` with `agent_id`, `role`, `capabilities`, message-bus subscription, and an inbox. Role subclasses:
- `PlannerAgent` — capability `plan`
- `WorkerAgent` — capability `execute`
- `ReviewerAgent` — capability `review`
- `CoordinatorAgent` — capability `coordinate`

Each implements `execute(task)` returning `(result, error)`. The base class reports results back to the message bus.

### 3.6 `swarm/swarm.py`

`Swarm` coordinates agents across a workflow:
- `default_swarm(name, human_author, auto_approve)` — creates a swarm with one coordinator, planner, worker, and reviewer.
- `add_agent(agent)` / `agent(agent_id)` / `agents()` — agent registry.
- `add_task(task)` — registers a task and logs an evidence artifact.
- `set_action_handler(handler)` — callback invoked when a task requires manual approval.
- `run(coordinator_id)` — executes the workflow in dependency order; respects approval gates and `failure_handling` (`stop` halts on first failure).
- `approve_action(action_id)` / `decline_action(action_id)` — gate operations that unblock or cancel the corresponding task.
- `summary()` — JSON-serializable snapshot of agents, tasks, actions, and the evidence record.

### 3.7 `swarm/cli.py`

CLI entry point `swarm`:
- `add --workflow <name> --task-id <id> --name <name> --command <cmd>... [--depends-on <d>...] [--requires-approval] [--timeout <n>] [--failure-handling stop|continue]`
- `run --workflow <name> [--coordinator <id>] [--auto-approve]` — `--auto-approve` is a commander opt-in for **compliance only**; it does NOT certify correctness
- `approve --action-id <id>` — satisfies the compliance gate; correctness stays `not_assessed`
- `decline --action-id <id>`
- `review-task --task-id <id> --reviewed-by <name> --correctness correct|incorrect|uncertain [--compliance compliant|non_compliant] [--reasoning <...>] [--notes <...>] [--commander-override]` — commander enforces correctness; AI does not self-certify
- `review-action --action-id <id> --reviewed-by <name> --correctness correct|incorrect|uncertain [--compliance compliant|non_compliant] [--reasoning <...>] [--notes <...>] [--commander-override]` — commander enforces correctness on an action
- `status --workflow <name>` — prints JSON summary including compliance and correctness per task/action
- `nlp` — interactive natural-language mode (see Section 4)

## 4. Natural-language (NLP) mode

`swarm nlp` starts an interactive REPL accepting sentence-style commands:

```
add task build command echo hello
add task test command pytest depends on build approval
run workflow release auto-approve
approve action action-test
decline action action-deploy
status workflow release
help
exit
```

Recognized verbs: `add/create/new`, `run/start/execute`, `approve/authorize`, `decline/reject`, `status/show/list`. Recognized keywords: `task`, `workflow`, `command`, `depends on`, `approval`.

Parsing is regex/shlex-based and best-effort; unrecognized input returns an error message. The NLP mode is a convenience wrapper over the same `Swarm` API used by the argparse subcommands.

## 5. Evidence record & attribution

The `EvidenceRecord` mirrors the agent-design schema (`design.md`, Section 1–8):

- `claims`: each claim has `claim_id`, `text`, `epistemic_status`, `support_status`, `source_ids`, `uncertainty`, `verification_criterion`, `limitations`.
- `sources`: each source has `source_id`, `title`, `access_status`, `source_category`, `claims_supported`, `support_summary`, `limitations`.
- `artifacts`: each artifact has `artifact_id`, `kind`, `identifier`, `existence_status`, `inspection_status`, `execution_status`, `risk_review`, `dry_run_or_sandbox_used`, `result_summary`.
- `actions`: each action has `action_id`, `action_type`, `external_or_state_changing`, `status`, `approval`, `reversibility`, `effects`, `side_effects`.
- `attribution`: `human_author`, `attribution_basis`, `ai_role` (const `"supporting_tool"`), `notes`.

The AI is framed explicitly as a supporting tool, not an autonomous decision-maker. Human authorship and approval are recorded explicitly.

## 6. Sandboxing / execution isolation — correctness statement

### 6.1 What the current implementation does

Task commands are executed by `Swarm._run_command` using `subprocess.run(command_list, cwd=..., capture_output=True, text=True, timeout=...)`. Key properties:

- The command is passed as a Python list, not a shell string, so shell-injection via metacharacters is avoided.
- `cwd` can be set to restrict the working directory.
- `timeout` bounds execution wall-clock time.
- stdout/stderr are captured and returned.

### 6.2 What the current implementation does NOT do

There is **no VM, container, process sandbox, namespace isolation, cgroup limit, seccomp filter, read-only rootfs, non-root user, or network egress control**. Commands run with the invoking user's privileges on the host kernel and can:

- Read/write any file the user can access.
- Access environment variables and secrets available to the user.
- Make outbound network connections.
- Spawn child processes.
- Consume unbounded CPU/memory (subject only to the `timeout`).

### 6.3 Research basis

The following sources were consulted (web search, 2026-11-17) and inform this assessment:

1. **MachineLearningMastery, "Sandboxing AI Agent Code Execution in Python: Containers, MicroVMs and Beyond"** (2026-11-11): Defines three isolation tiers — limited subprocess (shares host kernel/files; use only for trusted code), Docker container (namespaces+cgroups, shared kernel; escapes possible via kernel bugs), and Firecracker microVM (own kernel, hardware boundary). States: "Use a limited subprocess only for code you trust."

2. **Docker Docs, "Isolation layers" / "Security model"**: Describes five isolation layers (hypervisor, network, Docker Engine, workspace, credential proxy) for Docker Sandboxes running agents in microVMs. Notes containers share the host kernel and that "Docker describes this as a hardware boundary" for microVMs.

3. **Fly.io, "How to Run LLM-Generated Python Safely"** (2026-10-06): States RestrictedPython "is not a sandbox system or a secured environment"; production model-written code should run in a separate VM. "A strong VM with open egress still lets code send your data out."

4. **Safeguard.sh, "Python Sandbox: How to Run Untrusted Code Safely"** (2026-05-15): Recommends non-root user, dropped capabilities, read-only rootfs, seccomp, CPU/memory limits, default-deny network. States: never run model-generated code in the application process.

5. **OpenComputer, "Every Approach, Honestly Ranked"** (2026-07-20): Ranks exec/eval (no isolation), RestrictedPython (not a sandbox), PyPy/seccomp (partial), WASM (strong for pure compute), containers (namespace boundary, shared kernel), microVMs (hardware boundary). "Containers are a namespace boundary, not a hardware one."

6. **Multigrid, "Sandboxing an Agent That Executes Code"** (2026-08-03): Provides a hardened `docker run` template (`--network=none --read-only --user 65534 --cap-drop=ALL --security-opt=no-new-privileges --pids-limit --memory --cpus`) and warns: "An agent shell tool is RCE you installed on purpose."

7. **Docker, "What is Sandbox Security?"** (2026-06-01): Five core components — process isolation, syscall filtering (seccomp), network segmentation, resource limits (cgroups), runtime monitoring.

8. **OpenHands Enterprise, "Running Docker in the Agent Sandbox"**: Runs in-sandbox Docker daemons without host socket, non-root, user-namespace remapping, no cluster credentials, no host networking.

### 6.4 Risk summary

| Risk | Current mitigation | Residual exposure |
|------|-------------------|-------------------|
| Shell injection | Command passed as list (no `shell=True`) | None from metacharacters |
| File system access | None (uses `cwd` only) | Full user-level FS access |
| Network egress | None | Outbound connections possible |
| Privilege escalation | None | Runs as invoking user |
| Resource exhaustion | `timeout` only | CPU/memory unbounded within timeout |
| Credential leakage | None | User env/secrets accessible |
| Cross-container/VM escape | N/A (no container/VM) | N/A — host execution |

### 6.5 Recommendation

For trusted local workflows (e.g., running your own build/test scripts), the current host-execution model with the approval gate is acceptable. For untrusted or model-generated commands, run the CLI inside a **container** (hardened per Multigrid/Safeguard templates) or a **microVM** (Firecracker/Kata) rather than on the host directly. This package does not provision a VM or container; the operator is responsible for the execution boundary.

## 7. Automation gating (pre-action checklist)

Consistent with `/home/kaden/Desktop/Agent-Docs/AGENTS.md` Section 2 and `Principle 2`:

1. **User approval** — state-changing tasks require `requires_approval=True` and explicit `approve_action` before execution.
2. **Scope confirmation** — the gate records `approved_scope` (the task name) and `target` (working directory).
3. **Rollback plan** — `reversibility` is recorded per action (`reversible`/`partly_reversible`/`irreversible`/`unknown`); operators should define rollback per task.
4. **Post-run verification** — task results/errors are recorded; `summary()` reports final statuses.

A successful test or generated plan is **not** itself authorization; a separate explicit approval step is required.

## 8. Usage examples

### 8.1 Add and run a workflow (auto-approve)

```bash
swarm add --workflow release --task-id lint --name lint --command python -m py_compile src/swarm/cli.py
swarm add --workflow release --task-id test --name test --command python -m pytest tests/ --depends-on lint
swarm run --workflow release --auto-approve
```

### 8.2 Add and run with manual approval

```bash
swarm add --workflow release --task-id deploy --name deploy --command echo deploying --depends-on test --requires-approval
swarm run --workflow release
# deploy is BLOCKED; approve when ready:
swarm approve --action-id action-deploy
```

### 8.3 NLP mode

```bash
swarm nlp
> add task build command echo hi
> run workflow release auto-approve
> status workflow release
> exit
```

### 8.4 Programmatic API

```python
from swarm.swarm import Swarm
from swarm.types import Task

s = Swarm.default_swarm(name="ci", auto_approve=True)
s.add_task(Task(task_id="build", name="build", command=["echo", "hi"],
                requires_approval=True))
s.add_task(Task(task_id="test", name="test", command=["python", "-m", "pytest", "tests/"], depends_on=["build"]))
statuses = s.run()
print(statuses)

# Commander enforces correctness (AI does not self-certify):
s.commander_review_task(
    review_id="r-1",
    reviewed_by="Caden McCullen",
    task_id="build",
    correctness="correct",
    compliance="compliant",
    reasoning="output matches expected",
    notes="verified",
)
```

### 8.5 Commander review examples

```bash
# Commander marks a task correct (evidence-supported):
swarm review-task --task-id build --correctness correct --reviewed-by "Caden McCullen" --reasoning "output matches expected"

# Commander marks an action incorrect despite compliance:
swarm review-action --action-id action-deploy --correctness incorrect --reviewed-by "Caden McCullen" --reasoning "result wrong though procedure followed"
```

### 8.6 Governance CLI commands

```bash
# AI proposes a claim with evidence metadata (evidence-based trust):
swarm add-claim --claim-id c-1 --text "The sky is blue" \
  --epistemic-status direct_observation \
  --source-ids s-1 \
  --uncertainty "low" \
  --verification-criterion "direct observation"

# Add an evidence source:
swarm add-source --source-id s-1 --title "NIST AI RMF" \
  --access-status opened_and_reviewed \
  --source-category government_publication

# Validate the governance record against the schema:
swarm validate

# Print the full governance record (schema-aligned JSON):
swarm governance
```

## 9. Governance Engine & JSON Schema

The formal governance architecture is defined in `docs/governance.schema.json` (JSON Schema draft-07) and implemented by `src/swarm/governance.py` (`GovernanceEngine`). The schema encodes the three governing principles as active constraints:

- **compliance_vs_correctness** — `ComplianceStatus` and `CorrectnessStatus` are tracked independently on every `Action` and `Task`.
- **evidence_based_trust** — every `Claim` requires `source_ids` and `reasoning_steps`; a claim cannot be `supported` without both.
- **hierarchical_authority** — `authority_model.commander_is_sole_correctness_authority` is `true`; `ai_may_not_self_certify_correctness` is `true`; `ai_role` is `"supporting_tool"`.

The `GovernanceEngine` enforces these at runtime:

- `draft_action()` — creates an action with compliance and correctness both `not_assessed`.
- `grant_compliance()` — satisfies the pre-action gate (approval, scope, prior-to-execution). Sets `compliance=compliant` only; correctness stays `not_assessed`.
- `commander_review()` — only the Commander may set `correctness`. `reviewed_by` must not be `"ai"` or `"supporting_tool"`.
- `ai_attempt_support()` — a claim can only be marked `supported`/`partly_supported` if it has `source_ids` AND `reasoning_steps`; otherwise a `GovernanceViolationError` is raised.
- `ai_propose_result()` — the AI proposes a result with uncertainty but does not set correctness.

The lightweight agent configuration is defined in `docs/agent_governance_schema.json`
and enforced by `src/swarm/agent_logic.py` (`AgentLogicEnforcer`). It requires:

- `compliance_equals_correctness` to be `false`;
- trust to be based on primary evidence or empirical reasoning;
- independent verification;
- commander approval for every state-changing action;
- the AI role to remain supportive rather than authoritative.

`AgentLogicEnforcer.evaluate_correctness()` is only an evidence pre-check. Its
`is_correct` field is not an authoritative correctness certification:
`correctness_status` remains `not_assessed` and
`ai_self_certified_correct` remains `false` until the human commander records
a review.
- `assert_ai_cannot_self_certify()` — verifies correctness is still `not_assessed` (AI has not touched it).
- `to_record_dict()` / `validation_errors()` — exports a schema-aligned record and reports structural violations.

### Governance validation errors

`swarm validate` (or `governance.validation_errors()`) reports:
- Missing top-level keys (`schema_version`, `governance`, `record`).
- Missing governance principles or authority-model flags.
- `attribution.ai_role` not equal to `"supporting_tool"`.
- `reasoning.ai_self_certified_correct` equal to `true`.
- A claim marked `supported` without `source_ids` or `reasoning_steps`.

## 10. Testing

Run the full suite:

```bash
python -m pytest tests/ -v
```

Results: 43 tests pass (21 swarm + 22 governance), covering agent capabilities, message bus, workflow dependency ordering, approval gating, compliance/correctness separation, evidence-based trust, hierarchical authority, AI non-self-certification, claim/source recording, governance schema validation, and NLP parsing.

Compilation: `python -m py_compile src/swarm/*.py tests/test_swarm.py` — clean.

## 11. Limitations and known issues

- **No sandbox/VM isolation** (Section 6). Commands run on the host with user privileges.
- **CLI statelessness**: each `swarm` invocation creates a fresh in-memory `Swarm`; `add` and `run` in separate processes do not share state. Use a single `run` invocation for a full workflow, or use the programmatic API for persistent state.
- **NLP parsing is best-effort**: regex/shlex-based; complex or ambiguous sentences may fail. Type `help` for examples.
- **Failure handling**: `stop` halts the dependency loop on the first failed task; dependent tasks remain `PENDING` (not executed). `continue` is accepted as a value but the loop currently breaks on any failure regardless; this should be aligned with the documented policy if `continue` semantics are required.
- **Approval callback**: `set_action_handler` is invoked for blocked tasks; in CLI `run` mode it prints a message but does not wait for input — use `swarm approve --action-id <id>` in a separate step.
- **Correctness is commander-enforced**: the AI never self-certifies correctness (`ai_self_certified_correct` is always `false`). Correctness must be set via `swarm review-task` / `review-action` by the human commander.
- **No persistence**: state is in-memory only; no `.hydra/`-style durable history or SQLite store is implemented in this package.

## 12. Alignment with existing project principles

This package follows the conventions and principles in `/home/kaden/Desktop/Agent-Docs/`:

- **Operational tone**: neutral, technical, concise, direct; no unrequested interpretation (AGENTS.md Section 1).
- **Automation gating**: explicit user confirmation before state-changing actions; pre-action checklist (AGENTS.md Section 2).
- **Verification & evidence**: claims carry epistemic/support metadata; sources carry access status and limitations (AGENTS.md Section 3).
- **Credit & authorship**: attribution to human author; `ai_role` const `"supporting_tool"`; AI framed as supporting tool (AGENTS.md Section 4).
- **No additional properties**: strict typing via dataclasses; no schema drift (design.md Section 5).

## 14. Governance Documents

The following documents in `docs/governance/` formalize the system's
operating principles:

- [`system-philosophy-summary.md`](governance/system-philosophy-summary.md) —
  Core principles: control, automation limits, collaboration, evidence,
  safety, and authorship/credit.
- [`communication-protocol.md`](governance/communication-protocol.md) —
  Neutral technical tone; preserving user agency during difficult requests.
- [`pre-action-gating-checklist.md`](governance/pre-action-gating-checklist.md) —
  Approval, scope confirmation, rollback plan, and post-run verification for
  any automation.
- [`source-verification-procedure.md`](governance/source-verification-procedure.md) —
  Verifying external tools, libraries, APIs, and scripts before use.
- [`disagreement-handling-playbook.md`](governance/disagreement-handling-playbook.md) —
  Keeping reasoning explicit; preventing opinion-to-fact reframing.
- [`evidence-review-step.md`](governance/evidence-review-step.md) —
  Supporting data or links per conclusion; flagging unverified claims.
- [`safety-impact-assessment.md`](governance/safety-impact-assessment.md) —
  Ensuring learning and growth without environmental or operational damage.
- [`authorship-credit-rules.md`](governance/authorship-credit-rules.md) —
  Attributing Caden McCullen; defining creditorship standards; noting AI's
  supportive role.
- [`research-to-outcome-workflow.md`](governance/research-to-outcome-workflow.md) —
  Checkpoints, logging, synthesis, and final deliverable criteria for
  tool-assisted research.
- [`alignment-checkpoint-form.md`](governance/alignment-checkpoint-form.md) —
  Completed between phases to verify alignment with governance principles.
- [`terminology_glossary.md`](../terminology_glossary.md) —
  Standardized terminology mapping (old term -> new term).

## 15. License

MIT
