"""Command-line interface for the swarm system.

Includes a traditional argparse mode and an interactive natural-language
(nlp) mode so commands can be issued as plain sentences such as:

    add task build command "echo hi"
    run workflow release auto-approve
    approve action action-build
    status workflow release
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
    run.add_argument("--auto-approve", action="store_true")

    approve = sub.add_parser("approve", help="Approve a pending action")
    approve.add_argument("--action-id", required=True)

    decline = sub.add_parser("decline", help="Decline a pending action")
    decline.add_argument("--action-id", required=True)

    status = sub.add_parser("status", help="Show swarm status")
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

    # add task <id> [name <name>] [command <cmd>...] [depends on <deps>] [approval]
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
            # strip trailing depends-on / approval clauses
            rest = re.split(r"\b(depends on|depends-on|approval|requires approval)\b", rest)[0]
            cmd["command_args"] = shlex.split(rest)
        dm = re.search(r"\bdepends on\b\s+(.+)", lower)
        if dm:
            dep_clause = dm.group(1)
            # stop at the approval keyword so it is not treated as a dependency
            dep_clause = re.split(r"\b(approval|requires approval)\b", dep_clause)[0]
            cmd["depends_on"] = shlex.split(dep_clause)
        else:
            cmd["depends_on"] = []
        if _match_any(lower, _APPROVAL_WORDS):
            cmd["requires_approval"] = True
        return cmd

    # run workflow <name> [auto-approve]
    if _match_any(lower, _COMMAND_ALIASES["run"]):
        cmd = {"command": "run"}
        m = re.search(r"\bworkflow\b\s+(\S+)", lower)
        if m:
            cmd["workflow"] = m.group(1)
        if "auto-approve" in lower or "auto approve" in lower:
            cmd["auto_approve"] = True
        return cmd

    # approve action <id>
    if _match_any(lower, _COMMAND_ALIASES["approve"]):
        cmd = {"command": "approve"}
        m = re.search(r"\baction\b\s+(\S+)", lower)
        if m:
            cmd["action_id"] = m.group(1)
        return cmd

    # decline action <id>
    if _match_any(lower, _COMMAND_ALIASES["decline"]):
        cmd = {"command": "decline"}
        m = re.search(r"\baction\b\s+(\S+)", lower)
        if m:
            cmd["action_id"] = m.group(1)
        return cmd

    # status workflow <name>
    if _match_any(lower, _COMMAND_ALIASES["status"]):
        cmd = {"command": "status"}
        m = re.search(r"\bworkflow\b\s+(\S+)", lower)
        if m:
            cmd["workflow"] = m.group(1)
        return cmd

    return {"command": "unknown", "raw": t}


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
    for tid, st in statuses.items():
        lines.append(f"  {tid}: {st.value}")
    return "\n".join(lines)


def _run_approve(swarm: Swarm, parsed: dict) -> str:
    action_id = parsed.get("action_id")
    if not action_id:
        return "Error: no action id specified. Try: approve action action-build"
    swarm.approve_action(action_id)
    return f"Approved {action_id}"


def _run_decline(swarm: Swarm, parsed: dict) -> str:
    action_id = parsed.get("action_id")
    if not action_id:
        return "Error: no action id specified. Try: decline action action-deploy"
    swarm.decline_action(action_id)
    return f"Declined {action_id}"


def _run_status(swarm: Swarm, parsed: dict) -> str:
    workflow = parsed.get("workflow", swarm.name)
    summary = swarm.summary()
    lines = [f"Status for workflow {workflow}:"]
    for tid, st in summary["tasks"].items():
        lines.append(f"  {tid}: {st}")
    for aid, st in summary["actions"].items():
        lines.append(f"  {aid}: {st}")
    return "\n".join(lines)


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
    if cmd == "status":
        return _run_status(swarm, parsed)
    return "Unknown command."


def _help_text() -> str:
    return (
        "Natural-language swarm commands:\n"
        "  add task <id> [name <n>] command <cmd>... [depends on <d>...] [approval]\n"
        "  run workflow <name> [auto-approve]\n"
        "  approve action <id>\n"
        "  decline action <id>\n"
        "  status workflow <name>\n"
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
        print(json.dumps({"approved": args.action_id}))
        return 0

    if args.command == "decline":
        print(json.dumps({"declined": args.action_id}))
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
