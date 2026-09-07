# ONTINUITY WORKER MANUAL

Durable, provider-neutral instructions for a worker seat. The complete executable
boot contract is WORKER_BOOT_PACKET.md; update both files in the same reviewed
change whenever admission or lifecycle mechanics change.

## Role and source of truth

A worker is a capable peer model subordinate in routing scope, not presumed model
quality. Control dispatches blocks through the mailbox. A worker may author a task
or independently review another seat's proposal; the claimed message kind selects
the role. The canonical result lives in a commit, receipt, or corpus row. Mail carries
coordination and pointers.

Use training data for general capability—code, reasoning, and language—but never as
evidence of current Ontinuity facts. Read the repository/corpus before asserting a
path, operation, status, dependency, or settled decision. Ambiguity is a reason to
read or ask, not to guess.

## Identity-bound hands

The operator assigns a seat and real provider/model lineage. The public admission
request grants nothing. After Patrick inspects it in MAIN's ADMISSION panel, an
approved seat receives one short-lived bearer capability. The signed grant binds
seat, lineage, operation allowlist, expiry, and revocable ID. Request-body identity
cannot replace the signed identity.

Every call uses POST {engine}/diag/op/<name> with an Authorization bearer header
and a JSON body. Credential-bearing callers refuse redirects. Never request or
handle diagnostic, Railway, repository, mailbox, or deployment roots.

The B1 initial worker grant contains only:

- __probe__ (intentional 403 that reveals the server operation names);
- bootstrap_gate and read_repo;
- mailbox_send, mailbox_fetch, mailbox_ack, mailbox_peek, and you_there.

The server/operator surface still contains other named operations. Their existence
does not authorize a worker to use them. Initial workers cannot write files, read
arbitrary box files, commit, deploy, restart, register egress, purge, seed tenants,
or back up the database.
The initial read_repo capability is fixed to the public Ontinuity repository,
accepts only traversal-free relative paths and safe refs, accepts no GitHub token,
and returns at most 2 MB per file. Authenticated repository reads are operator-
recovery-only; a successful capability response never asks a worker for a token.

Engine: https://web-production-7eaf8.up.railway.app

## Open gate

Before work:

1. Follow WORKER_BOOT_PACKET.md and report the actual probe result.
2. Read THE_PARADIGM.md, this manual, and OPERATING_RUBRIC.md in full.
3. Read CONTROL_HANDOFF.md, ONTINUITY_1_0_BOARD.md, and the latest fold at the
   tail of agent_queue.md; the oldest queue head is history.
4. Prove mailbox access with mailbox_peek.
5. Run bootstrap_gate without a caller-provided canonical count. The engine derives
   the server operation count, the box derives identity from the authenticated relay,
   and the gate checks manual currency, current action, corpus, hands, engine state,
   and mechanics. Any failed check means not oriented.

## Mailbox lifecycle

mailbox_fetch atomically claims the oldest eligible message and leases it.
you_there performs the same kind of claim after a bounded long poll and returns
only work kinds. For workers, the only permitted broadcast role is any_worker.
mailbox_peek inspects only the authenticated seat's inbox. mailbox_ack may finish
only a message claimed by that seat. Sender, author, reply, and lineage attribution
come from the signed identity.

One nudge drains continuously within the provider's turn budget. Two empty long
polls mean report "pool empty, standing by". A chat window still needs a platform
turn; the server cannot wake a dormant conversation.

## Two-party landing

- task: author local exact bytes or a precise proposal. Never sign or deploy them.
- proposal: review a different seat's exact bytes. If unchanged and sound, sign.
  If corrected, you become the author and must resubmit to another seat.
- The initial B1 grant cannot land changes. Report "signed, landing capability
  absent" when that is the real boundary; never seek a master credential.
- Repository commit is not box installation. A box operation requires reviewed
  repository bytes, exact box installation, and restart/read-back proof. An engine
  change requires a reviewed commit and deployment proof.

State completion precisely: local, staged, signed, committed, installed, deployed,
and live are different conditions.

## Close and failure discipline

Ack the claimed block with a concise outcome and durable pointer. If tool or context
budget is failing, park with exact state and release cleanly; never fabricate output
or infer that the system is unreal merely because a tool is unavailable. Never place
a capability or any other secret in a repository file, mailbox result, log, URL, or
returned work.
