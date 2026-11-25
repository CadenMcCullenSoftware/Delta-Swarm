# Buyer Handoff Overview

**Status:** Draft for review; not an offer or statement of work.

**Prepared:** 2026-11-25

**Release:** `v1.0.1` (package metadata version `1.0.1`; record the full tag
commit with `git rev-parse v1.0.1` after publication)

Repository: [CadenMcCullenSoftware/Delta-Swarm](https://github.com/CadenMcCullenSoftware/Delta-Swarm)

## What Swarm does

Swarm is a local Python workflow orchestrator. It runs configured task
commands in dependency order, records workflow and evidence data in memory,
and can require explicit human approval before marked actions run. Approval
records procedural compliance; a human commander separately reviews
correctness.

The current source includes the Python package, command-line interface,
governance configuration and schemas, terminology glossary, and governance
guides. Workflow state is in memory. Separate CLI invocations do not share
tasks or evidence; use the Python API in one process or the `swarm nlp` REPL
for a multi-step workflow. Persistent CLI state is not included. In
particular, `swarm validate` checks a fresh default record; it cannot validate
claims added by a previous CLI invocation.

Commands run on the host with the invoking user's privileges. The package
does not provide sandboxing, container or VM isolation, network isolation, or
resource limits.

## Setup and verification

Requirements: Python 3.10 or newer and pip.

```bash
git clone https://github.com/CadenMcCullenSoftware/Delta-Swarm.git
cd Delta-Swarm
git checkout v1.0.1
git rev-parse HEAD
python -m pip install -e '.[dev]'
python -m py_compile src/swarm/*.py
python -m pytest tests/ -v
python -m json.tool docs/governance.schema.json > /dev/null
python -m json.tool docs/agent_governance_schema.json > /dev/null
python -m json.tool docs/agent_governance_config.example.json > /dev/null
swarm governance-load --config docs/agent_governance_config.example.json
swarm validate
swarm --help
```

Run the complete command list on the delivered tag and record the actual
results, Python version, operating system, and full commit hash in the
acceptance record. The expected test count is not a substitute for the
recorded test output.

## Included scope and boundaries

- Workflow tasks, dependency ordering, in-memory status and evidence records.
- A Python API and CLI for adding and running tasks, approval decisions,
  commander reviews, governance checks, and config loading.
- Governance schemas, example configuration, and the included governance and
  terminology documents.

Task commands run on the host with the invoking user's privileges. The package
does not provide a sandbox, container, VM, network isolation, or resource
limits. It does not persist workflow state between processes. Sandboxing,
persistence, custom adapters, and production deployment support require
separate scope and acceptance criteria.

## Access, license, and ownership status

The repository is public on GitHub and includes an MIT `LICENSE` identifying
Caden McCullen as copyright holder. Confirm the license and any buyer-specific
terms before delivery. A source archive does not contain Git history; provide
the tagged repository or an agreed Git bundle when full history is required.

No terms for ownership or licensing of custom configuration, implementation,
or other buyer-specific work are defined in this repository. Put those terms
in a separate signed statement of work before custom work begins.
