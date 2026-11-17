# Source Verification Procedure

Verifies that any cited external tool, library, API, link, script, file, or
package is checked against primary sources and explicit evidence before use.

## Step 1: Inventory the Citation

Record the source identifier, title, author or publisher, URL, publication
date, accessed date, access status, source category, and limitations.

## Step 2: Verify Availability

Confirm the public domain or link is available and accessible. Record
`access_status` (e.g., `opened_and_reviewed`, `not_checked`, `unavailable`).

## Step 3: Verify Existence and Applicability

Confirm that referenced scripts, files, or packages exist and are applicable to
the intended use. Check primary sources (official documentation, repository,
or publisher) rather than secondary summaries.

## Step 4: Verify Runnable Script

Before a script can be used, confirm it includes an applicable, runnable
script. The script must be executable in a controlled environment (sandbox,
container, or microVM) and must not expose secrets or keys.

## Step 5: Record Units and Baseline

Check units and baseline values against primary sources. Record
`units_and_baseline_checked` as true or false.

## Step 6: Record Limitations

Document any limitations of the source, including access restrictions,
version constraints, or applicability boundaries.

## Step 7: Update Support Status

Only mark a claim as `supported` or `partly_supported` if it has both
`source_ids` and `reasoning_steps`. Otherwise the claim remains `unverified`.

## Output

A structured source record with:
- `source_id`, `title`, `author_or_publisher`, `url`
- `access_status`, `source_category`
- `claims_supported`, `support_summary`
- `units_and_baseline_checked`
- `limitations`

## Rule

Unverified claims are flagged as needing validation and are not presented as
established facts.
