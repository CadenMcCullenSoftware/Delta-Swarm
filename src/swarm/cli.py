"""Command-line interface for the swarm system.

Includes a traditional argparse mode and an interactive natural-language
(nlp) mode. The CLI enforces the separation between compliance (procedure
followed) and correctness (evidence-supported result): the AI does not
self-certify correctness; only the human commander reviews correctness.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys

from .swarm import Swarm
from .types import Task, TaskStatus


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swarm",
        description="Multi-agent swarm system for user-controlled workflow execution",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Add a task to the workflow")
    add.add_argument("--workflow", required=True)
    add.add_argument("--task-id", required=True)
    add.add_argument("--name", required=True)
    add.add_argument("--command", required=True, nargs="+")
    add.add_argument("--depends-on", nargs="*", default=[])
    add.add_argument("--requires-approval", action="store_true")
    add.add_argument("--timeout", type=int, default=None)
    add.add_argument("--failure-handling", default="stop")

    run = sub.add_parser("run", help="Run the workflow")
    run.add_argument("--workflow", required=True)
    run.add_argument("--coordinator", default="coordinator-1")
    run.add_argument("--auto-approve", action="store_true",
                     help="Commander opt-in for COMPLIANCE only. Does not certify correctness.")

    approve = sub.add_parser("approve", help="Approve a pending action (compliance gate)")
    approve.add_argument("--action-id", required=True)

    decline = sub.add_parser("decline", help="Decline a pending action")
    decline.add_argument("--action-id", required=True)

    review_task = sub.add_parser("review-task",
                                 help="Commander enforces correctness on a task")
    review_task.add_argument("--task-id", required=True)
    review_task.add_argument("--reviewed-by", required=True)
    review_task.add_argument("--correctness", required=True,
                             choices=["correct", "incorrect", "uncertain"],
                             help="Correctness assessment. Commander enforces; AI does not self-certify.")
    review_task.add_argument("--compliance", default="compliant",
                             choices=["compliant", "non_compliant"])
    review_task.add_argument("--reasoning", default="")
    review_task.add_argument("--notes", default=None)
    review_task.add_argument("--commander-override", action="store_true")

    review_action = sub.add_parser("review-action",
                                   help="Commander enforces correctness on an action")
    review_action.add_argument("--action-id", required=True)
    review_action.add_argument("--reviewed-by", required=True)
    review_action.add_argument("--correctness", required=True,
                               choices=["correct", "incorrect", "uncertain"])
    review_action.add_argument("--compliance", default="compliant",
                               choices=["compliant", "non_compliant"])
    review_action.add_argument("--reasoning", default="")
    review_action.add_argument("--notes", default=None)
    review_action.add_argument("--commander-override", action="store_true")

    add_claim = sub.add_parser("add-claim",
                               help="AI proposes a claim with evidence metadata")
    add_claim.add_argument("--claim-id", required=True)
    add_claim.add_argument("--text", required=True)
    add_claim.add_argument("--epistemic-status", default="unknown",
                           choices=["source_reported_fact", "direct_observation",
                                    "calculation", "inference",
                                    "causal_hypothesis",
                                    "opinion_or_recommendation", "unknown"])
    add_claim.add_argument("--source-ids", nargs="*", default=[])
    add_claim.add_argument("--uncertainty", default="")
    add_claim.add_argument("--verification-criterion", default=None)

    add_source = sub.add_parser("add-source",
                                help="Add an evidence source")
    add_source.add_argument("--source-id", required=True)
    add_source.add_argument("--title", required=True)
    add_source.add_argument("--access-status", default="not_checked")
    add_source.add_argument("--source-category", default="other")

    validate = sub.add_parser("validate",
                              help="Validate governance record against schema")

    governance = sub.add_parser("governance",
                                help="Print the full governance record (schema-aligned JSON)")

    governance_check = sub.add_parser("governance-check",
                                      help="Evaluate a proposal against evidence (compliance != correctness)")
    governance_check.add_argument("--claim-id", required=True)
    governance_check.add_argument("--text", required=True)
    governance_check.add_argument("--syntax-valid", action="store_true")
    governance_check.add_argument("--instruction-followed", action="store_true")
    governance_check.add_argument("--causally-sound", action="store_true")
    governance_check.add_argument("--primary-source", action="append", default=[],
                                  help="Primary verified source id (repeatable)")
    governance_check.add_argument("--source-id", action="append", default=[],
                                  help="Source id (repeatable)")

    governance_load = sub.add_parser("governance-load",
                                     help="Load and validate an agent governance config JSON file")
    governance_load.add_argument("--config", required=True)

    status = sub.add_parser("status", help="Show swarm status (compliance + correctness)")
    status.add_argument("--workflow", required=True)

    nlp = sub.add_parser("nlp", help="Interactive natural-language command mode")

    return parser


# ---------- natural language parsing ----------

_COMMAND_ALIASES = {
    "add": ["add", "create", "new"],
    "run": ["run", "start", "execute"],
    "approve": ["approve", "authorize", "ok"],
    "decline": ["decline", "reject", "deny", "cancel"],
    "status": ["status", "show", "list"],
    "review": ["review", "assess"],
}

_TASK_WORDS = ["task", "job", "step"]
_WORKFLOW_WORDS = ["workflow", "pipeline", "swarm"]
_COMMAND_WORDS = ["command", "cmd", "run", "with"]
_APPROVAL_WORDS = ["approval", "approve", "authorized", "approved"]


def _tokens(text: str) -> list[str]:
    return shlex.split(text)


def _match_any(text: str, words: list[str]) -> bool:
    lower = text.lower()
    return any(w in lower for w in words)


def parse_nlp(text: str) -> dict | None:
    """Parse a plain-language sentence into a structured command dict."""
    t = text.strip()
    if not t:
        return None
    lower = t.lower()

    if lower in {"help", "?"}:
        return {"command": "help"}

    if _match_any(lower, _COMMAND_ALIASES["add"]):
        cmd: dict = {"command": "add"}
        m = re.search(r"\btask\b\s+(\S+)", lower)
        if m:
            cmd["task_id"] = m.group(1)
        m = re.search(r"\bname\b\s+(\S+)", lower)
        if m:
            cmd["name"] = m.group(1)
        else:
            cmd["name"] = cmd.get("task_id", "task")
        cm = re.search(r"\bcommand\b\s+(.+)", lower)
        if cm:
            rest = cm.group(1)
            rest = re.split(r"\b(depends on|depends-on|approval|requires approval)\b", rest)[0]
            cmd["command_args"] = shlex.split(rest)
        dm = re.search(r"\bdepends on\b\s+(.+)", lower)
        if dm:
            dep_clause = dm.group(1)
            dep_clause = re.split(r"\b(approval|requires approval)\b", dep_clause)[0]
            cmd["depends_on"] = shlex.split(dep_clause)
        else:
            cmd["depends_on"] = []
        if _match_any(lower, _APPROVAL_WORDS):
            cmd["requires_approval"] = True
        return cmd

    if _match_any(lower, _COMMAND_ALIASES["run"]):
        cmd = {"command": "run"}
        m = re.search(r"\bworkflow\b\s+(\S+)", lower)
        if m:
            cmd["workflow"] = m.group(1)
        if "auto-approve" in lower or "auto approve" in lower:
            cmd["auto_approve"] = True
        return cmd

    if _match_any(lower, _COMMAND_ALIASES["approve"]):
        cmd = {"command": "approve"}
        m = re.search(r"\baction\b\s+(\S+)", lower)
        if m:
            cmd["action_id"] = m.group(1)
        return cmd

    if _match_any(lower, _COMMAND_ALIASES["decline"]):
        cmd = {"command": "decline"}
        m = re.search(r"\baction\b\s+(\S+)", lower)
        if m:
            cmd["action_id"] = m.group(1)
        return cmd

    if _match_any(lower, ["review task"]):
        cmd = {"command": "review-task"}
        m = re.search(r"\btask\b\s+(\S+)", lower)
        if m:
            cmd["task_id"] = m.group(1)
        return cmd

    if _match_any(lower, ["review action"]):
        cmd = {"command": "review-action"}
        m = re.search(r"\baction\b\s+(\S+)", lower)
        if m:
            cmd["action_id"] = m.group(1)
        return cmd

    if _match_any(lower, _COMMAND_ALIASES["status"]):
        cmd = {"command": "status"}
        m = re.search(r"\bworkflow\b\s+(\S+)", lower)
        if m:
            cmd["workflow"] = m.group(1)
        return cmd

    return {"command": "unknown", "raw": t}


# ---------- command handlers (argparse mode) ----------

def _run_add(swarm: Swarm, parsed: dict) -> str:
    task_id = parsed.get("task_id")
    if not task_id:
        return "Error: no task id specified. Try: add task build command echo hi"
    name = parsed.get("name", task_id)
    cmd_args = parsed.get("command_args", [])
    if not cmd_args:
        return "Error: no command specified. Try: add task build command echo hi"
    task = Task(
        task_id=task_id,
        name=name,
        command=cmd_args,
        depends_on=parsed.get("depends_on", []),
        requires_approval=parsed.get("requires_approval", False),
        timeout=parsed.get("timeout"),
        failure_handling=parsed.get("failure_handling", "stop"),
    )
    swarm.add_task(task)
    return f"Added task {task_id} to workflow {swarm.name}"


def _run_run(swarm: Swarm, parsed: dict) -> str:
    workflow = parsed.get("workflow", swarm.name)
    auto = parsed.get("auto_approve", False)

    def on_action(action_id: str, task_name: str) -> None:
        print(f"ACTION REQUIRES APPROVAL: {action_id} ({task_name})")

    swarm.set_action_handler(on_action)
    statuses = swarm.run(coordinator_id="coordinator-1")
    lines = [f"Ran workflow {workflow} (auto_approve={auto})"]
    lines.append("NOTE: auto_approve satisfies COMPLIANCE only; correctness is NOT self-certified.")
    for tid, st in statuses.items():
        lines.append(f"  {tid}: status={st.value}")
    return "\n".join(lines)


def _run_approve(swarm: Swarm, parsed: dict) -> str:
    action_id = parsed.get("action_id")
    if not action_id:
        return "Error: no action id specified. Try: approve action action-build"
    swarm.approve_action(action_id)
    return (f"Approved {action_id} (compliance gate satisfied). "
            f"Correctness remains NOT_ASSESSED until commander review.")


def _run_decline(swarm: Swarm, parsed: dict) -> str:
    action_id = parsed.get("action_id")
    if not action_id:
        return "Error: no action id specified. Try: decline action action-deploy"
    swarm.decline_action(action_id)
    return f"Declined {action_id}"


def _run_review_task(swarm: Swarm, parsed: dict) -> str:
    task_id = parsed.get("task_id")
    if not task_id:
        return "Error: no task id specified. Try: review-task --task-id build --correctness correct --reviewed-by <name>"
    reviewed_by = parsed.get("reviewed_by")
    if not reviewed_by:
        return "Error: --reviewed-by is required (commander enforces correctness)."
    correctness = parsed.get("correctness")
    swarm.commander_review_task(
        review_id=f"review-{task_id}",
        reviewed_by=reviewed_by,
        task_id=task_id,
        correctness=correctness,
        compliance=parsed.get("compliance", "compliant"),
        reasoning=parsed.get("reasoning", ""),
        notes=parsed.get("notes"),
        commander_override=parsed.get("commander_override", False),
    )
    return (f"Commander {reviewed_by} reviewed task {task_id}: correctness={correctness}. "
            f"The AI did not self-certify; correctness was enforced by the commander.")


def _run_review_action(swarm: Swarm, parsed: dict) -> str:
    action_id = parsed.get("action_id")
    if not action_id:
        return "Error: no action id specified."
    reviewed_by = parsed.get("reviewed_by")
    if not reviewed_by:
        return "Error: --reviewed-by is required."
    correctness = parsed.get("correctness")
    swarm.commander_review_action(
        review_id=f"review-{action_id}",
        reviewed_by=reviewed_by,
        action_id=action_id,
        correctness=correctness,
        compliance=parsed.get("compliance", "compliant"),
        reasoning=parsed.get("reasoning", ""),
        notes=parsed.get("notes"),
        commander_override=parsed.get("commander_override", False),
    )
    return (f"Commander {reviewed_by} reviewed action {action_id}: correctness={correctness}.")


def _run_add_claim(swarm: Swarm, parsed: dict) -> str:
    """AI proposes a claim with evidence metadata (evidence-based trust).

    The AI sets epistemic_status, uncertainty, sources, and reasoning steps,
    but support_status starts as UNVERIFIED. The AI may not self-certify
    support.
    """
    claim_id = parsed.get("claim_id")
    text = parsed.get("text")
    if not claim_id or not text:
        return "Error: --claim-id and --text are required."
    swarm.governance.add_claim(
        claim_id=claim_id,
        text=text,
        epistemic_status=parsed.get("epistemic_status", "unknown"),
        source_ids=parsed.get("source_ids", []),
        uncertainty=parsed.get("uncertainty", ""),
        verification_criterion=parsed.get("verification_criterion"),
    )
    return (f"AI proposed claim {claim_id}. support_status=unverified "
            f"(AI does not self-certify support; evidence required).")


def _run_add_source(swarm: Swarm, parsed: dict) -> str:
    source_id = parsed.get("source_id")
    title = parsed.get("title")
    if not source_id or not title:
        return "Error: --source-id and --title are required."
    swarm.governance.add_source(
        source_id=source_id,
        title=title,
        access_status=parsed.get("access_status", "not_checked"),
        source_category=parsed.get("source_category", "other"),
    )
    return f"Added source {source_id}: {title}"


def _run_validate(swarm: Swarm, parsed: dict) -> str:
    errors = swarm.governance.validation_errors()
    if errors:
        return "GOVERNANCE VALIDATION FAILED:\n" + "\n".join(f"  - {e}" for e in errors)
    return "GOVERNANCE VALIDATION PASSED: record conforms to governance schema."


def _run_governance(swarm: Swarm, parsed: dict) -> str:
    return json.dumps(swarm.governance.to_record_dict(), indent=2)


def _run_governance_check(swarm: Swarm, parsed: dict) -> str:
    """Evaluate a proposal against evidence (compliance != correctness).

    Uses the AgentLogicEnforcer to demonstrate that surface compliance does
    not equal correctness and that evidence is required for trust.
    """
    from .agent_logic import AgentLogicEnforcer

    enforcer = AgentLogicEnforcer(engine=swarm.governance,
                                  commander_present=True)

    proposal = {
        "claim_id": parsed.get("claim_id"),
        "text": parsed.get("text"),
        "syntax_valid": parsed.get("syntax_valid", False),
        "instruction_followed": parsed.get("instruction_followed", False),
        "causally_sound": parsed.get("causally_sound", False),
        "action_name": parsed.get("claim_id"),
    }

    evidence = [
        {"source_id": sid, "is_primary_source": True, "verified": True}
        for sid in parsed.get("primary_source", [])
    ]
    # Include non-primary sources too (should not count toward trust)
    for sid in parsed.get("source_id", []):
        if sid not in parsed.get("primary_source", []):
            evidence.append({"source_id": sid, "is_primary_source": False, "verified": True})

    eval_res = enforcer.evaluate_correctness(proposal, evidence)
    return json.dumps(eval_res, indent=2)


def _run_governance_load(swarm: Swarm, parsed: dict) -> str:
    """Load and validate an agent governance config JSON file."""
    import json as _json
    config_path = parsed.get("config")
    try:
        with open(config_path) as f:
            config = _json.load(f)
    except (OSError, _json.JSONDecodeError) as exc:
        return f"Error loading config {config_path}: {exc}"

    # Validate required structure per agent_governance_schema.json
    errors = []
    role = config.get("role_definition", {})
    if role.get("ai_role") not in ("SUPPORTIVE_TOOL", "ANALYTICAL_ACCELERATOR"):
        errors.append("role_definition.ai_role must be SUPPORTIVE_TOOL or ANALYTICAL_ACCELERATOR")
    if role.get("commander_role") not in ("HUMAN_COMMANDER", "FINAL_AUTHORITY"):
        errors.append("role_definition.commander_role must be HUMAN_COMMANDER or FINAL_AUTHORITY")

    vp = config.get("verification_policy", {})
    if vp.get("compliance_equals_correctness") is not False:
        errors.append("verification_policy.compliance_equals_correctness must be false")
    if vp.get("trust_foundation") not in ("PRIMARY_EVIDENCE", "EMPIRICAL_REASONING"):
        errors.append("verification_policy.trust_foundation must be PRIMARY_EVIDENCE or EMPIRICAL_REASONING")
    if vp.get("require_independent_verification") is not True:
        errors.append("verification_policy.require_independent_verification must be true")

    eg = config.get("execution_gate", {})
    if eg.get("commander_approval_required") is not True:
        errors.append("execution_gate.commander_approval_required must be true")
    if eg.get("action_type") not in ("READ_ONLY_PROPOSAL", "STATE_CHANGING_ACTION"):
        errors.append("execution_gate.action_type must be READ_ONLY_PROPOSAL or STATE_CHANGING_ACTION")

    if errors:
        return "GOVERNANCE CONFIG INVALID:\n" + "\n".join(f"  - {e}" for e in errors)
    return f"GOVERNANCE CONFIG VALID: {config_path} (ai_role={role.get('ai_role')}, commander_role={role.get('commander_role')})"


def _run_status(swarm: Swarm, parsed: dict) -> str:
    workflow = parsed.get("workflow", swarm.name)
    summary = swarm.summary()
    lines = [f"Status for workflow {workflow}:"]
    lines.append("Compliance = procedure followed. Correctness = evidence-supported (commander-enforced).")
    for tid, info in summary["tasks"].items():
        lines.append(f"  {tid}: status={info['status']} "
                     f"compliance={info['compliance']} "
                     f"correctness={info['correctness']} "
                     f"commander_reviewed={info['commander_reviewed']}")
    for aid, info in summary["actions"].items():
        lines.append(f"  {aid}: approval={info['approval']} "
                     f"compliance={info['compliance']} "
                     f"correctness={info['correctness']} "
                     f"commander_reviewed={info['commander_reviewed']}")
    rec = summary["record"]
    lines.append(f"Attribution: human_author={rec['attribution']['human_author']} "
                 f"ai_role={rec['attribution']['ai_role']}")
    lines.append(f"AI self-certified correct: {rec['reasoning']['ai_self_certified_correct']}")
    return "\n".join(lines)


# ---------- NLP handling ----------

def handle_nlp(swarm: Swarm, parsed: dict) -> str:
    cmd = parsed.get("command")
    if cmd == "help" or cmd is None:
        return _help_text()
    if cmd == "unknown":
        return f"Could not understand: {parsed.get('raw')}. Type 'help' for examples."
    if cmd == "add":
        return _run_add(swarm, parsed)
    if cmd == "run":
        return _run_run(swarm, parsed)
    if cmd == "approve":
        return _run_approve(swarm, parsed)
    if cmd == "decline":
        return _run_decline(swarm, parsed)
    if cmd == "review-task":
        # NLP review-task needs --reviewed-by; best-effort: prompt via structured fields absent
        return ("review-task requires --reviewed-by and --correctness. "
                "Use the argparse form: swarm review-task --task-id <id> --correctness correct --reviewed-by <name>")
    if cmd == "review-action":
        return ("review-action requires --reviewed-by and --correctness. "
                "Use the argparse form: swarm review-action --action-id <id> --correctness correct --reviewed-by <name>")
    if cmd == "status":
        return _run_status(swarm, parsed)
    return "Unknown command."


def _help_text() -> str:
    return (
        "Natural-language swarm commands:\n"
        "  add task <id> [name <n>] command <cmd>... [depends on <d>...] [approval]\n"
        "  run workflow <name> [auto-approve]   (auto-approve = compliance only, not correctness)\n"
        "  approve action <id>\n"
        "  decline action <id>\n"
        "  status workflow <name>\n"
        "  review-task / review-action require --reviewed-by and --correctness (use argparse form)\n"
        "  help | exit\n"
    )


def _nlp_repl() -> int:
    swarm = Swarm.default_swarm(name="default")
    print("Swarm NLP mode. Type 'help' for examples, 'exit' to quit.")
    while True:
        try:
            text = input("swarm> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not text:
            continue
        if text.lower() in {"exit", "quit", "q"}:
            return 0
        parsed = parse_nlp(text)
        print(handle_nlp(swarm, parsed))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "add":
        swarm = Swarm.default_swarm(name=args.workflow)
        task = Task(
            task_id=args.task_id,
            name=args.name,
            command=args.command,
            depends_on=args.depends_on,
            requires_approval=args.requires_approval,
            timeout=args.timeout,
            failure_handling=args.failure_handling,
        )
        swarm.add_task(task)
        print(json.dumps({"added": args.task_id, "workflow": args.workflow}))
        return 0

    if args.command == "run":
        swarm = Swarm.default_swarm(name=args.workflow, auto_approve=args.auto_approve)

        def on_action(action_id: str, task_name: str) -> None:
            print(f"ACTION REQUIRES APPROVAL: {action_id} ({task_name})")

        swarm.set_action_handler(on_action)
        statuses = swarm.run(coordinator_id=args.coordinator)
        print(json.dumps(statuses, indent=2))
        return 0

    if args.command == "approve":
        swarm = Swarm.default_swarm(name="default")
        swarm.approve_action(args.action_id)
        print(json.dumps({"approved": args.action_id, "note": "compliance only; correctness NOT_ASSESSED"}))
        return 0

    if args.command == "decline":
        swarm = Swarm.default_swarm(name="default")
        swarm.decline_action(args.action_id)
        print(json.dumps({"declined": args.action_id}))
        return 0

    if args.command == "review-task":
        swarm = Swarm.default_swarm(name="default")
        swarm.commander_review_task(
            review_id=f"review-{args.task_id}",
            reviewed_by=args.reviewed_by,
            task_id=args.task_id,
            correctness=args.correctness,
            compliance=args.compliance,
            reasoning=args.reasoning,
            notes=args.notes,
            commander_override=args.commander_override,
        )
        print(json.dumps({
            "reviewed": args.task_id,
            "reviewed_by": args.reviewed_by,
            "correctness": args.correctness,
            "compliance": args.compliance,
            "note": "Commander enforced correctness; AI did not self-certify.",
        }, indent=2))
        return 0

    if args.command == "review-action":
        swarm = Swarm.default_swarm(name="default")
        swarm.commander_review_action(
            review_id=f"review-{args.action_id}",
            reviewed_by=args.reviewed_by,
            action_id=args.action_id,
            correctness=args.correctness,
            compliance=args.compliance,
            reasoning=args.reasoning,
            notes=args.notes,
            commander_override=args.commander_override,
        )
        print(json.dumps({
            "reviewed": args.action_id,
            "reviewed_by": args.reviewed_by,
            "correctness": args.correctness,
            "compliance": args.compliance,
            "note": "Commander enforced correctness; AI did not self-certify.",
        }, indent=2))
        return 0

    if args.command == "add-claim":
        swarm = Swarm.default_swarm(name="default")
        print(_run_add_claim(swarm, vars(args)))
        return 0

    if args.command == "add-source":
        swarm = Swarm.default_swarm(name="default")
        print(_run_add_source(swarm, vars(args)))
        return 0

    if args.command == "validate":
        swarm = Swarm.default_swarm(name="default")
        print(_run_validate(swarm, vars(args)))
        return 0

    if args.command == "governance":
        swarm = Swarm.default_swarm(name="default")
        print(_run_governance(swarm, vars(args)))
        return 0

    if args.command == "governance-check":
        swarm = Swarm.default_swarm(name="default")
        print(_run_governance_check(swarm, vars(args)))
        return 0

    if args.command == "governance-load":
        swarm = Swarm.default_swarm(name="default")
        print(_run_governance_load(swarm, vars(args)))
        return 0

    if args.command == "status":
        swarm = Swarm.default_swarm(name=args.workflow)
        print(json.dumps(swarm.summary(), indent=2))
        return 0

    if args.command == "nlp":
        return _nlp_repl()

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
