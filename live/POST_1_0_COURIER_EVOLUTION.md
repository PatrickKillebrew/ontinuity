# POST-1.0 COURIER EVOLUTION

**Status:** deferred roadmap; not an Ontinuity 1.0 build order  
**Established:** 2026-09-04  
**Controlling dependency:** `live/ONTINUITY_1_0_COMPLETION_PLAN.md`  
**Purpose:** preserve improvements discovered while evaluating the courier without allowing them to interrupt the current finish line.

---

## 1. SETTLED ARCHITECTURAL JUDGMENT

The courier is not a temporary workaround to be replaced after Ontinuity matures. Its ordinary HTTPS boundary is the system's portable narrow waist:

- models and providers sit outside it;
- the engine admits calls through one authenticated surface;
- named operations bound what a seat may do;
- the mailbox carries the exclusive durable work lifecycle;
- the ledger records material action;
- the corpus preserves institutional meaning and history.

The primitives resemble an API gateway, capability RPC surface, durable work queue, lease-based worker pool, and audit log. The Ontinuity-specific contribution is their composition into an institution that separates intelligence, authority, memory, review, and deployment.

**Constitutional invariant:** there is one authoritative work path. A task that does not enter the mailbox lifecycle and evidence chain does not become Ontinuity work. Future interfaces may translate into this path; they may not create a parallel source of truth.

The July 20 ruling remains controlling: seating another provider is normally a staffing/configuration event, not permission to invent another harness. The September 3 OpenAI succession proved that the existing corpus, HTTPS courier, and mailbox can cross provider and chat-platform boundaries without an OpenAI-specific engine rebuild.

## 2. WHY THE KNOWN-GOOD CURL MATTERS

HTTPS is the protocol; curl is only the verified reference client. Python libraries, browser fetch, SDKs, and provider tools can issue similar requests, but their network permissions, proxy paths, request encoding, headers, and WAF treatment may differ.

The recurring failure was not ignorance of HTTP. It was substitution: a seat replaced the corpus-proven request with a familiar generic client, then treated the generic client's failure as evidence about Ontinuity. The durable correction is:

1. run the platform network-admission check;
2. reproduce the known-good request exactly;
3. distinguish pre-HTTP transport denial from HTTP authentication/application results;
4. classify before redesigning;
5. treat an alternate client as a new implementation requiring proof, never as an equivalent by assumption.

This is why the reference curl remains valuable even if a later deterministic client wraps it.

## 3. ALREADY REQUIRED FOR 1.0 — DO NOT DEFER

The following improvement belongs to B1/RC-2 and RC-3, not this post-1.0 queue:

- operator-approved, short-lived, revocable, identity-bound capabilities;
- operation allowlists attached to the admitted identity;
- seat and lineage derived from authentication rather than trusted body fields;
- master credentials retained server-side;
- authenticated occupant/action provenance.

This closes the shared-`DIAG_KEY` and self-asserted-identity boundary. The post-1.0 work below assumes B1 already exists.

## 4. DEFERRED IMPROVEMENTS

### C1 — Versioned courier and mailbox schemas

Define machine-readable schemas for operation requests, responses, mailbox envelopes, evidence references, failures, and lifecycle transitions. Include at minimum:

- protocol/schema version;
- authenticated actor identity;
- message, block, correlation, and causation identifiers;
- operation or message kind;
- lifecycle state;
- evidence/provenance references;
- timestamps and expiry;
- structured error class.

Publish an OpenAPI/JSON Schema contract and generate compatibility tests from it. Do not change the mailbox lifecycle merely to resemble an external standard.

**Promotion condition:** move into B6/RC-7 only if clean installation, cross-provider boot, or outside-operator transfer cannot be made reproducible without it.

### C2 — Idempotency and replay safety

Give every state-changing request an idempotency key and persist the resulting disposition. A retried commit, deploy, acknowledgement, correction, or close must return the original result or refuse safely rather than repeat the side effect.

The useful idea from CloudEvents is stable event identity and a common envelope; adoption of the whole specification is optional. Ontinuity's evidence semantics remain authoritative.

**Promotion condition:** move into 1.0 only if B3-B6 tests reproduce duplicate side effects, ambiguous retries, or replay-dependent corruption.

### C3 — End-to-end trace correlation

Carry one trace/correlation identity across intake or design objective, mailbox dispatch, claim, implementation, review, correction, signoff, deployment, session persistence, and corpus close. Exporting that path through OpenTelemetry may later provide vendor-neutral traces, metrics, and logs.

The trace is observability, not the evidence source of truth. Ontinuity's database, receipts, mailbox, commits, and corpus remain the authoritative record.

**Promotion condition:** B5/RC-6 must first attempt the complete evidence chain with existing records. Add tracing only if missing runtime correlation prevents diagnosis or traversal.

### C4 — Deterministic portable client

Build a small provider-neutral client only after the HTTPS contract stabilizes. Candidate commands:

- `ontinuity preflight`
- `ontinuity probe`
- `ontinuity claim`
- `ontinuity respond`
- `ontinuity ack`
- `ontinuity op <name>`

The client should perform network-admission diagnosis, schema validation, safe header authentication, timeouts, structured error classification, idempotency, and redacted logging. Curl remains the transparent reference underneath or beside it.

The client must not become a second harness, contain provider SDK assumptions, hide authoritative responses, or permit operations outside the server allowlist.

**Promotion condition:** post-1.0 by default. Promote only if RC-1, RC-7, or RC-9 repeatedly fails because capable seats cannot reliably reproduce the documented HTTPS calls.

### C5 — Governor event stream

Replace or supplement polling with a read-only Server-Sent Events stream carrying mailbox, operation-ledger, session, review, and deployment state changes. Governor renders durable records; it does not run models and does not create a second mutation channel.

Polling remains a valid fallback. Streaming must never be required for correctness.

**Promotion condition:** post-1.0 unless B9 outside-operator testing proves polling prevents adequate diagnosis or safe operation.

### C6 — Standards-compatible façades

Evaluate external interoperability only after Ontinuity 1.0 is coherent:

- **A2A façade:** translate external task/message/artifact calls into authenticated Ontinuity mailbox blocks and lifecycle transitions.
- **MCP façade:** expose approved courier reads/tools to MCP-capable clients while still enforcing Ontinuity identity, operation bounds, ledgering, and mailbox rules.
- **CloudEvents envelope:** optionally map exported events into a common vendor-neutral event shape.
- **OpenTelemetry export:** optionally emit correlated operational telemetry.

These are adapters at the boundary, never alternative internal authorities. If an adapter cannot preserve identity, no-self-certification, lifecycle, evidence, and fail-closed behavior, it is incompatible and must refuse.

**Promotion condition:** a real integration partner or release-adjacent customer must require the standard. Standards availability alone is not a build reason.

## 5. ORDER AFTER 1.0

When the controlling completion plan is satisfied, reconsider this roadmap in dependency order:

1. Re-read release-test and outside-review findings.
2. Remove proposals whose problem did not materialize.
3. Promote only evidence-backed needs.
4. Stabilize schemas before generating a client or compatibility façade.
5. Add idempotency before increasing worker scale or external ingress.
6. Add trace export and Governor streaming as observability layers.
7. Add A2A/MCP/CloudEvents compatibility only for a named consumer.

Each promoted item becomes its own work block with an author, independent reviewer, acceptance test, rollback boundary, and corpus close. This document is a parking place for earned possibilities, not standing authorization to build them.

## 6. REFERENCES FOR LATER EVALUATION

- A2A: https://github.com/a2aproject/A2A
- Model Context Protocol: https://modelcontextprotocol.io/specification/2026-07-28
- CloudEvents: https://cloudevents.io/
- OpenTelemetry tracing: https://opentelemetry.io/docs/concepts/signals/traces/

External standards change. Re-read their current specifications when this roadmap is activated; do not implement later from this 2026 snapshot alone.

