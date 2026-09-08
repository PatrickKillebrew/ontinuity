# Trusted exact-commit deploy protocol

Status: local B1 candidate; not live until exact-byte independent review,
authorized box install/restart, commit publication, and staged cutover proof.

## Caller contract

`POST /op/deploy` accepts one JSON object with exactly four string keys:

- `action`: `start` or `status`
- `target`: `main` or `farm`
- `signoff_block_id`: the bounded mailbox block identifier
- `commit_sha`: exactly 40 lowercase hexadecimal characters

No other key is accepted. The caller cannot name a provider, URL, header, query,
project, environment, service, provider deployment ID, log option, credential,
shell command, dry-run mode, or box target.

The initial Control and Worker grants remain unchanged. A public request for the
single operation `deploy` creates only a pending HIGH-IMPACT request with a maximum
TTL of 300 seconds; its TTL must be a JSON integer and is never coerced from a
boolean, float, or string. That request must also contain exactly one `deploy_scope`
object with `signoff_block_id`, lowercase 40-hex `commit_sha`, and
`target_scope` (`main|farm|both`). Elevation is derived from the exact deploy-only
operation set, not selected by the caller; inconsistent stored elevation or scope
metadata fails closed. The immutable scope is stored in the pending request,
displayed in the operator panel and confirmation, signed into the capability, and
matched again to the issued registry record. MAIN refuses a deploy body whose
block, commit, or target falls outside it before relay.

The mailbox proposal and latest signoff for the block must carry the identical
canonical ref `deploy:v1:<target_scope>:<commit_sha>`. The box derives the only
acceptable refs from the requested target and commit and compares them before any
provider action. Thus a `both` signoff can stage the same reviewed commit through
MAIN and FARM; a target-specific signoff authorizes only that target. A capability-
authenticated caller must also be the distinct-seat signer recorded for the
proposal. Operator-root calls remain transition/recovery only.

## Two phases and replay

Both phases use the same endpoint and exact tuple. They fit the existing 25-second
courier relay and 30-second compiled-client bound; neither timeout is widened.

`start` requires a successful operations-ledger begin before any provider action.
Under one fixed cross-process lock, it derives a SHA-256 tracking ID from the
block, target, and commit. It atomically persists and directory-fsyncs a mode-600
pre-mutation record before contacting the provider. After a canonical provider
deployment ID returns, it atomically advances the same record to `accepted`.

Before any accepted, pending, or terminal replay is returned, the adapter proves
the stored provider, project, environment, and service identifiers still match
the current trusted server configuration. Repeating a bound accepted tuple returns
its box-owned record without another provider mutation. If the provider response
reached the box but the caller lost the box or
relay response, a new compiled request using the same tuple recovers safely. If a
process or provider call fails between pre-mutation persistence and accepted-state
persistence, the record remains `mutation_pending` or `mutation_unknown`. `start`
and `status` then return HTTP 409 and never retry or query automatically. An
operator must reconcile that UNKNOWN state against provider records before any
manual state repair; absence cannot be inferred from a timeout.

`status` loads the stored tuple and provider deployment ID. It queries a bounded
provider status window and accepts exactly one row with that ID, the fixed target
service, and the requested commit. Another or older SUCCESS row cannot substitute.
Pending, success, and failure are explicit. Terminal state is persisted once;
later status calls return it without provider traffic. A terminal provider failure
finishes the operations ledger as failure.

Every path after a successful ledger begin attempts ledger finish. Provenance
records contain bounded lifecycle metadata and the box tracking ID, never provider
credentials or response bodies.

## Trusted adapter boundary

Provider dispatch occurs only inside `live/box/trusted_deploy.py`. The model-facing
request and operator approval flow remain provider-neutral. A different provider
requires a reviewed server adapter; an unknown configured provider fails closed.

The selected internal adapter owns a fixed HTTPS endpoint, authentication header,
credential, project/environment/target identifiers, provider request documents,
status window, and failure-log limit. Those provider-specific values are not part
of this public caller protocol. They remain confined to reviewed trusted adapter
code, its tests, and operator recovery material. The adapter invokes only the
fixed `curl --config -` executable shape without a shell, supplies its private
configuration on stdin, disables redirects, constrains the protocol to HTTPS,
uses an eight-second provider timeout plus a fixed process deadline, and bounds
each provider response body to 256 KiB. It captures exactly three HTTP-status
digits after that bounded body and accepts only status 200 through 299 before
parsing the body. The child receives a fresh minimal environment and isolates
curl's user default configuration without repurposing general home/configuration
variables. There is no alternate Python HTTP fallback.

Failure-log message bytes are read only to validate and bound the provider
response. No message text, transformed message, or message hash reaches the caller,
provenance ledger, or operations ledger. The caller receives only bounded count,
fixed-vocabulary severity-count, and first/last timestamp metadata. Unknown or
unrecognized provider severity text maps to the fixed `unknown` category rather
than becoming a response key. Provider timestamps must be RFC3339 with a timezone
and are normalized to exact UTC before storage or return. Persisted summaries
enforce the availability flag against every other field: unavailable and zero-line
states have exact empty/null metadata, while positive-line states have strictly
positive severity counts that sum to the line count and ordered canonical UTC
timestamps.

## Cutover order

1. Install exact `box_ops.py` and `trusted_deploy.py` beside one another, install
   the rest of the box manifest, restart the workspace under the rollback engine,
   and verify every installed hash.
2. Using operator transition/recovery authority and the existing two-party block,
   call `start` for MAIN at the exact reviewed commit. Recover with `status` using
   the same tuple; fail-stop on UNKNOWN, wrong ID, wrong service, wrong commit, or
   provider failure.
3. After MAIN returns at that commit, invoke fixed `restart_burnin` and prove the
   named resident service active while FARM remains rollback.
4. Issue an explicitly approved deploy-only capability to the FARM signer. Use
   `start` then separate `status` calls for FARM at the same exact commit.
5. Run the complete Control and Worker capability approval, denial, expiry, and
   revocation proofs.
