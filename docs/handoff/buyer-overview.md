# Buyer Handoff Overview

**Draft prepared:** 2026-11-25  
**Candidate version:** `1.0.0` (from `pyproject.toml`; annotated tag `v1.0.0`
created locally, push pending GitHub credentials)

## What Swarm does

Swarm is a local Python workflow orchestrator. It runs configured task commands
in dependency order, records workflow and evidence data in memory, and can
require an explicit human approval before marked actions run. Approval records
procedural compliance; a human commander separately reviews correctness.

The current source includes the Python package, command-line interface,
governance configuration and schemas, terminology glossary, and governance
guides. The source repository history should be provided through GitHub access
or a Git bundle; a source archive by itself does not contain commit history.

## Setup and verification

Requirements: Python 3.10 or newer and pip.

```bash
git clone https://github.com/CadenMcCullenSoftware/Delta-Swarm.git
cd Delta-Swarm
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

The release-candidate verification on 2026-11-25 passed all 50 tests, bytecode
compilation, JSON parsing, the governance config load, schema validation, CLI
help, and a `Swarm.default_swarm(...).run()` smoke check. Repeat these checks on
the delivered tag and record that tag's commit hash in the acceptance record.

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

The repository metadata and README declare MIT, and a `LICENSE` file (MIT,
rightsholder Caden McCullen) has been added to the tree. GitHub access for a
buyer has not been provisioned or confirmed (push pending credentials).
Resolve access before granting buyer access or delivering a tagged source
bundle.

No terms for ownership or licensing of custom configuration, implementation,
or other buyer-specific work are defined in this repository. Put those terms
in a separate signed statement of work before custom work begins.
