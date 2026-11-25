# Swarm Pilot Offer Sheet

**Draft for discussion — confirm scope, fee, and terms in a signed statement
of work before presenting as an offer.**

| Commercial field | Agreed value |
| --- | --- |
| Buyer and legal entity | `[complete]` |
| Provider and legal entity | `[complete]` |
| Selected pilot and fixed fee | `[select / confirm]` |
| Payment schedule and due dates | `[agree in writing]` |
| Start date and delivery date | `[complete]` |
| Named human commander | `[complete]` |
| Repository tag and full commit | `v1.0.1` / `[record after publication]` |

## Draft pilot options

These are proposed package boundaries for discussion, not approved commercial
terms. Confirm what is included, delivery dates, payment schedule, and any
applicable taxes in the signed statement of work.

| Draft fee | Proposed scope |
| --- | --- |
| **$149 — Guided evaluation** | One setup and verification walkthrough in one agreed Python environment; no custom workflow implementation. |
| **$499 — Single-workflow pilot** | Configure and verify one buyer-approved local workflow through the Python API in one process, then provide a concise verification record. |
| **$1,500 — Limited integration pilot** | Scope and verify one workflow for one agreed repository, including only the specifically listed configuration or integration changes in the signed statement of work. |

No duration, payment split, support period, or outcome guarantee is implied by
these draft prices. Do not start paid or custom work until both parties sign
the scope and commercial terms.

## Proposed base delivery

1. Provide access to the agreed tagged Swarm source and its full Git history.
2. Help the buyer install the package in one agreed Python 3.10+ environment.
3. Configure and verify one buyer-approved local workflow through the Python
   API in one process. The buyer supplies the commands and confirms the target
   environment and permissions. Persistent CLI state is not included.
4. Deliver a verification record listing the exact tag and commit, commands
   run, results, known limitations, and outstanding issues.
5. Hold a handoff review and obtain the buyer's written acceptance or issue
   list.

Changes to the package, extra workflows, or work beyond these items require a
written scope and fee change approved by both parties before that work starts.

## Explicit exclusions and optional add-ons

The base delivery does not include sandboxing or VM/container deployment,
persistent storage, custom adapters, production hosting, security operations,
ongoing support, or a service-level commitment. Each can be separately scoped,
priced, and accepted in writing.

## Terms and sign-off

Repository metadata says MIT and a `LICENSE` file (MIT, rightsholder Caden
McCullen) is included. Confirm the base license and distributable terms before
source delivery. Ownership or licensing of custom configuration and
implementation work must be stated in the signed statement of work; this
draft assigns no rights by itself.

Before work begins, both parties record the scope, target environment,
permissions, fee, schedule, license/access terms, acceptance checks, and named
human commander. At close, the commander reviews the verification record,
limitations, and any change requests and records acceptance or an issue list.
