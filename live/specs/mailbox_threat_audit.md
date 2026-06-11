# Mailbox / Courier Threat Audit — cross-seat & impersonation surface
Block: SECAUDIT-1 | Seat: worker2 | Lineage: claude:opus-4.8 | Lease: 2026-06-11T02:05:22Z
Grounding: read seat_mailbox.py (425 lines), box_ops.py (256), file_server.py ledger section — all via /diag/op/read_file off the live box. Live-verified against operations_ledger + seat_mailbox rows. NOT read: app.py (the Railway ENGINE courier) — different host, unreachable via box-scoped read_file. Claims about the engine-side courier are labeled INFERENCE.

## Root condition
One shared diag key authorizes every courier op for every node (control, worker1, worker2 all carry the same key, per the boot packets). The diag gate — secrets.compare_digest(X-Diag-Key, dk) in _diag_ok() (seat_mailbox.py L108-119, box_ops.py L39-45) — proves only "a holder of THE key is calling." It never establishes WHICH seat. Every seat identity in the system (from_seat, author_seat, claimed_by, the reply routing, the ledger caller) is therefore self-asserted in the request body, not derived from authentication. The four questions below are all facets of this single fact.

## Q1 — Can mailbox_send set an arbitrary from_seat / author_seat / from_lineage?  EXPLOITABLE
mailbox_send (seat_mailbox.py L135-167) reads from_seat, to_seat, kind straight from the JSON body (L140-142) and inserts them verbatim (L153-161). from_lineage is body-supplied (L156). author_seat defaults to from_seat but is independently overridable from the body (L160); author_lineage likewise (L161). Nothing cross-checks any of these against the caller, because the caller has no authenticated identity — only the shared key.
Consequence: any node can author or send a message AS any other node, with any lineage stamp. worker2 can post a message with from_seat="control", from_lineage="claude:opus-4.8", and it is indistinguishable from a real control message. The "lineage honest everywhere" standing rule is a HONOR-SYSTEM convention today, structurally unenforced.
Severity: HIGH. This is the broadest hole: it forges the identity other safeguards trust.

## Q2 — Can mailbox_ack / mailbox_reclaim act on a msg the caller did NOT claim?  EXPLOITABLE
mailbox_ack (L226-258): the UPDATE keys on msg_id ALONE — "SET status='done' ... WHERE msg_id=? AND status!='done'" (L238-239). There is no AND claimed_by=<caller> clause, and no caller identity is even passed in. Any keyholder can ack ANY msg_id, including a block currently leased to another worker. The auto-generated reply is then routed using the ORIGINAL row's from_seat/to_seat (L244, L251), so the forged ack even looks correctly addressed.
mailbox_reclaim (L285-301): UPDATE returns all expired claims to queued with no caller scoping (L294-295). It only touches rows already past lease_until, so it cannot steal a LIVE claim — but any keyholder can sweep, and reclaim semantics let a second node legitimately re-claim a block whose lease was force-expired. Lower severity than ack because it respects the lease clock.
Consequence (ack): node X can mark node Y's in-flight block done and inject a result reply attributed to Y. This directly defeats accountability — a block can be "completed" by someone who never did it.
Severity: ack HIGH; reclaim LOW/DEPENDS (bounded by the lease timer).

## Q3 — Does mailbox_fetch / you_there let a caller claim while CLAIMING TO BE another seat?  EXPLOITABLE (and it weakens NOSELF-1)
mailbox_fetch (L170-223) and you_there/_yt_try_claim (L334-420) take seat, roles, and lineage from the body (L178, L182, L389-394) and write that seat into claimed_by (L210-211, L363-364). The claim is atomic against DOUBLE-claim (BEGIN IMMEDIATE, L188 / L341 — this part is sound; it is what makes "exactly one winner" true), but it does nothing to authenticate that the caller IS the seat it names.
Critical downstream effect on NOSELF-1: the no-self-sign-off guard (_noself_predicate, L50-61) excludes reviewable items where COALESCE(author_seat,from_seat)=seat OR author_lineage=lineage — using the SELF-ASSERTED seat/lineage from the SAME request body. A node that wants to review (or sign off on) its own work can simply claim with a different seat/lineage string and the filter passes it through. NOSELF-1 is only as strong as the honesty of the seat field it filters on, and that field is attacker-controlled.
Severity: HIGH — not for the claim itself (atomicity holds) but because it is the bypass for the no-self-sign-off integrity property the system is being built to guarantee.

## Q4 — What does operations_ledger.caller actually record — self-asserted or derived from auth?  NEITHER (records auth METHOD, not identity)
_ops_begin(operation, tier, caller, source_ip, args) (file_server.py L1417-1427) inserts caller verbatim. Every call site passes the literal string "diag-key" (L1297, L1459, L1478; box_ops _ledger_begin L48-53; seat_mailbox _ledger L124-132). So caller is a constant denoting the auth method, never the seat.
source_ip = request.remote_addr — LIVE-VERIFIED as the engine relay egress (52.9.6.176), identical for every seat, because all seat traffic is forwarded through the one courier. It does not distinguish nodes.
The only seat identifier that reaches the ledger is inside args for the mailbox ops (e.g. {"seat": "...", "roles": [...]}, L185) — and that is the same self-asserted, forgeable body field from Q1/Q3.
Live confirmation: last ledger rows all show caller="diag-key", source_ip="52.9.6.176", args carrying only the self-declared values.
Consequence: the audit spine cannot answer "which seat did this." Forensics after an impersonation event would show only "the key did it, via the relay." 
Severity: HIGH for accountability — there is no authenticated actor record anywhere in the system.

## Severity ranking (worst first)
1. Q4 — no authenticated actor in the ledger. Foundational: even detection/forensics is blind. (Also the reason the others are unfalsifiable after the fact.)
2. Q1 — forgeable from_seat/author/lineage on send. Forges the identity everything else trusts.
3. Q3 — claim/fetch identity is self-asserted AND is the input to NOSELF-1; it is the structural bypass of the no-self-sign-off property.
4. Q2 ack — any keyholder acks/replies for any block, defeating completion accountability.
5. Q2 reclaim — sweep is unscoped but lease-bounded; lowest.

## Does per-identity keys (vs shared key) close these?
Per-identity keys are NECESSARY but NOT SUFFICIENT, and only if the code stops trusting body-supplied identity and starts deriving it from the key.
- Closes well (with code change): Q4 — map key->seat at the gate, write the DERIVED seat as caller. Q1 — reject/override from_seat,author_seat,lineage unless they match the key's identity. Q2 ack — add AND claimed_by = <key-derived seat>. Q3 — feed the NOSELF filter and claimed_by the DERIVED seat, not the body field.
- INFERENCE (labeled, since I could not read engine app.py): the engine courier currently forwards the seat fields from the body untouched. Per-identity keys only help if the gate that VALIDATES the key also INJECTS the derived identity and the downstream routes IGNORE the body's identity fields. Issuing distinct keys while still reading from_seat/seat from the body would leave every hole above open — the key would prove "a valid node" without binding the asserted seat to it.
- Independent of keys: the ACK ownership check (claimed_by scoping) and a reclaim caller-scope are cheap hardening worth doing regardless.

## Recommendation for the per-identity-key build (threat-model input)
1. Gate derives identity: key -> (seat, lineage). Store a key->seat map server-side.
2. All write/claim/ack/send routes: derive seat/lineage from the authenticated key; treat body from_seat/author_seat/lineage/seat as REQUESTS, reject or override on mismatch — never trust them as identity.
3. mailbox_ack: WHERE msg_id=? AND claimed_by=<derived_seat>. mailbox_reclaim: optionally scope or restrict to a coordinator identity.
4. Ledger: write derived seat as a real actor column (separate from caller="diag-key"); keep source_ip but stop treating it as identity (it is always the relay).
5. NOSELF-1: filter on derived author identity, not body-supplied — otherwise it is bypassable by relabeling.

## Honest limits of this audit
- app.py (Railway engine courier) NOT READ — unreachable from the box. All claims about what the engine does with seat fields are INFERENCE and marked so.
- Atomicity of the claim (no double-claim) is verified by reading the BEGIN IMMEDIATE transaction; I did not run a concurrent live race to empirically prove it.
- Read-only block: no code changed. This report staged to the box for control review + commit.
