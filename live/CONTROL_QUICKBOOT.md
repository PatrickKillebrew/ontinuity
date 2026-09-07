# CONTROL QUICK-BOOT PACKET

This is the provider-neutral standing packet for a fresh Ontinuity Control seat.
The operator assigns the seat and its real provider/model lineage. Models receive
only an operator-approved, short-lived capability; diagnostic, Railway, repository,
mailbox, and deployment roots remain outside the model conversation.

## 0. Request bounded hands

Use the assigned identity exactly. Do not invent or alter it. Submit this public,
non-authorizing request:

```sh
ENGINE=https://web-production-7eaf8.up.railway.app
curl -sS -X POST "$ENGINE/diag/admission/request" \
  -H "Content-Type: application/json" \
  -d '{"seat":"control","lineage":"<<ACTUAL-PROVIDER:MODEL/INSTANCE>>","operations":["__probe__","bootstrap_gate","read_repo","mailbox_send","mailbox_fetch","mailbox_ack","mailbox_peek","you_there"],"ttl_seconds":900}'
```

Report the returned request ID. Patrick opens the existing MAIN page, chooses
`ADMISSION`, inspects the exact seat, lineage, operations, and lifetime, and either
approves or declines. Approval displays a bearer capability once. Receive that
capability privately and hold it only in memory or a mode-600 ephemeral file. Never
print, commit, mail, or include it in returned work.

Set `ONTINUITY_CAPABILITY` in the current shell. If the request or approval is not
available, stop and report the actual response; do not seek a master credential.

## 1. Confirm real hands

```sh
curl -sS -X POST "$ENGINE/diag/op/__probe__" \
  -H "Authorization: Bearer $ONTINUITY_CAPABILITY" \
  -H "Content-Type: application/json" -d '{}'
```

`__probe__` intentionally returns 403 with the live courier allowlist. Report the
operation names actually returned. A caller-platform network denial is not a
Railway or credential failure; report the layer that denied the request.

## 2. Ground through five required corpus read groups (six files total)

Read each file in full with `POST /diag/op/read_repo`, the bearer header, and body
`{"path":"live/<file>","ref":"main"}`. Do not substitute a platform connector or
memory. Report one real current line from every group:

1. `CONTROL_HANDOFF.md` — state its single next action.
2. `THE_PARADIGM.md` — corpus facts outrank model priors.
3. `OPERATING_RUBRIC.md` — state the distinct-author/deployer invariant.
4. `OPERATING_MANUAL.md` — read the open/close rituals, cold boot, transport,
   install, session-start, and configuration traps.
5. `PUNCH_LIST.md` plus the latest fold at the tail of `agent_queue.md` — the
   queue's oldest head is history.

Then call `bootstrap_gate` with the assigned identity, `role: control`, and your
own reproductions of its four mechanics invariants. Treat `oriented: true` as the
mechanical check; never override a canonical count in the request body.

## 3. Operating boundary

- Ground every load-bearing Ontinuity claim in a read shown in the same message.
- Repository commit is not box installation. Installed bytes and repository bytes
  are separate facts until compared.
- The initial capability cannot write, commit, deploy, restart, purge, seed, read
  arbitrary box files, or register egress. If work reaches one of those boundaries,
  stage locally, state exactly what is ready, and return to the operator.
- Its `read_repo` operation is fixed to the public Ontinuity repository, accepts
  only traversal-free relative paths and safe refs, accepts no repository
  credential, and returns at most 2 MB per file. Authenticated repository reads
  are operator-recovery-only.
- An author never signs or deploys its own bytes. A correcting reviewer becomes the
  author and must obtain a distinct reviewer.
- Mailbox messages coordinate work and carry pointers; the canonical result lives
  in the repository, receipt, or corpus row.
- At context loss, park with an exact handoff. Never fabricate missing tool output.

At close, reconcile the punch list, conversation record, queue tail, manual and boot
packet currency, secret-regression scan, and the next single action. Distinguish
local, staged, committed, installed, deployed, and live.

Boot now: obtain the bounded capability, run the probe, complete all five read
groups and the bootstrap gate, then report current state and the single next action.
