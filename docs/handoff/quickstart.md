# Pilot Quickstart and Verification

Use the tagged source in a disposable or otherwise approved environment.
Commands executed by Swarm run with the invoking user's host privileges; this
project does not provide a sandbox, VM/container isolation, network isolation,
or resource limits.

## Install

```bash
git clone https://github.com/CadenMcCullenSoftware/Delta-Swarm.git
cd Delta-Swarm
git checkout v1.0.1
git rev-parse HEAD
python --version
python -m pip install -e '.[dev]'
```

Record the full commit hash and environment in the acceptance checklist.
The package requires Python 3.10 or newer.

## Verify

```bash
python -m py_compile src/swarm/*.py
python -m pytest tests/ -v
python -m json.tool docs/governance.schema.json > /dev/null
python -m json.tool docs/agent_governance_schema.json > /dev/null
python -m json.tool docs/agent_governance_config.example.json > /dev/null
swarm governance-load --config docs/agent_governance_config.example.json
swarm validate
swarm --help
```

`swarm validate` validates a fresh default record. Separate CLI invocations
create separate in-memory swarms and do not share tasks or evidence.

## Python API smoke check

```python
from swarm.swarm import Swarm
from swarm.types import Task

swarm = Swarm.default_swarm(name="pilot-smoke")
swarm.add_task(Task(
    task_id="smoke",
    name="smoke",
    command=["python", "-c", "print('pilot smoke ok')"],
))
print(swarm.run())
```

Run the snippet from the repository root in the installed environment. Record
the command output and task status. This smoke check runs a local command; use
only a command and environment approved by the human commander.
