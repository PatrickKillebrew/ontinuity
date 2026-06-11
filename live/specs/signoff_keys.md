# SIGNOFF-KEYS — peer review of per-identity keys (KEYS-2)
Reviewer: worker2 (claude:opus-4.8) | Author: worker1 | distinct seats
Grounding: read live file_server.py (authenticate_identity/_kr_* L1408-1487), seat_mailbox.py (_authed_identity/_trusted_seat L143-167, mailbox_send L178-209, fetch L213+, ack L270+, reclaim L352+, you_there L473+, _noself_predicate L50-61), box_ops.py (KEYS-2 helpers + /op/deploy bind, read in SIGNOFF-DEPLOYCHAIN), against live/specs/per_identity_keys.md. Live-checked the repo for staged plaintext keys. Inference labeled.

## VERDICT: REJECT — one required route (mailbox_send) is unmigrated, leaving the Q1 hole open
The auth CORE is correct and 4 of 5 identity-writing routes are properly migrated. But mailbox_send — the route the spec's own §3 lists FIRST as the broadest hole (Q1) — still trusts the body and is the one route that writes author_seat/author_lineage. Because the two-party deploy gate and no-self-sign-off both depend on those authorship fields, leaving send unmigrated means even WITH per-identity keys a forger can author a proposal or signoff as any seat, and the guarantees the other routes establish stay bypassable. This is a structural gap, not a nit, so per the block it is a REJECT with the exact fix below. Everything else is sign-off-ready.

## What is CORRECT (verified, would pass on its own)
- CHECK 1 identity DERIVED from key: PASS. file_server.authenticate_identity (L1432-1465) hashes the presented key (sha256) and constant-time-compares against a hash->identity registry; a hit returns {seat,lineage,authenticated:True,mode:per_identity}; revoked status returns authenticated:False (fails closed); unknown key -> None (401). Identity is the lookup RESULT, never a parsed prefix. _trusted_seat (sm L155-167) is the single chokepoint: when authenticated it returns the key-derived seat and IGNORES the body; only in shared mode does it fall back to the body seat.
- CHECK 2 no plaintext keys at rest: PASS. Registry stores sha256 only (L1410-1413, _kr_hash L1420-1421). register_seat_key stores only the hash, never logs plaintext (L1467+). Live repo check: live/seat_keys.json is ABSENT from the repo (404 on read_repo) — nothing plaintext staged; the registry is box/vault-populated. Hash-only is repo-safe.
- CHECK 3 (routes USE derived identity) PASS for fetch/ack/reclaim/you_there: all four call _trusted_seat and use the derived seat — fetch writes claimed_by from it (L220,253), ack guards WHERE claimed_by=seat (L284,301), reclaim scopes to seat (L364,372), you_there claims as the derived seat (L473) and feeds _noself_predicate the derived seat+lineage (L436). _noself_predicate (L50-61) filters on COALESCE(author_seat,from_seat)=seat — and is now fed the DERIVED seat on the claim path, so no-self-sign-off-on-CLAIM is unbypassable once keys are on. 
- CHECK 4 body-spoof IGNORED when authenticated: PASS for the migrated routes — _trusted_seat returns key identity and discards body_seat when ident.authenticated (sm L159-161). (FAILS for send — see flaw.)
- CHECK 5 shared DIAG_KEY still works (no lockout): PASS. authenticate_identity maps the shared key to {seat:unattributed, authenticated:False, mode:shared} (L1462-1464); _trusted_seat falls back to the body seat in that mode. Empty registry -> shared-key mode for everyone (L1425,1430). Migration can roll seat-by-seat, no flag day.

## THE FLAW (exact)
mailbox_send (seat_mailbox.py L178-209) does NOT call _authed_identity/_trusted_seat at all (confirmed: grep of the function body shows no ident/authed reference; only _diag_ok() L179). It reads from_seat (L182), from_lineage (L198), author_seat (L202), author_lineage (L203) straight from the body and INSERTS them verbatim. So under a per-identity key:
- a caller can still send a message with from_seat = any other seat (Q1 forge-sender), and
- can set author_seat/author_lineage to any seat — which is the authorship the no-self-sign-off filter and the /op/deploy two-party gate (_twoparty_check reads proposal author_seat + signoff from_seat) rely on.
Net: the claim path is hardened but the AUTHORSHIP path is not. A node can author its own proposal as "worker1" and sign it off as "worker2" by sending two forged-from_seat messages — defeating the two-party rule I signed off in SIGNOFF-DEPLOYCHAIN, even after keys are issued. The migrated routes give a false sense of closure while the highest-ranked hole (Q1) is still open. INFERENCE (labeled): this looks like an omission — send was simply missed in the route sweep — not a deliberate exception, since the spec §3 explicitly requires it and the other four routes follow the pattern.

## THE FIX (small, matches the established pattern)
In mailbox_send, after parsing the body, derive identity and override:
```
seat, lin, authed = _trusted_seat(b.get("from_seat"), b.get("from_lineage"))
if authed:
    # body from_seat is a REQUEST; reject mismatch, never trust it as identity
    if (b.get("from_seat") or "").strip() and (b.get("from_seat").strip() != seat):
        return jsonify({"error":"from_seat does not match authenticated identity"}), 409
    from_seat = seat
    from_lineage = lin
    # author defaults to the authenticated sender; dispatch-on-behalf (author_seat !=
    # sender) allowed ONLY for a coordinator-role key (spec §3 narrow exception), else force:
    author_seat = (b.get("author_seat") or seat)
    if not _is_coordinator(ident) and author_seat != seat:
        author_seat = seat   # refuse silent impersonation
    author_lineage = lin
# shared-key mode: unchanged (body-asserted, honest-but-unauthenticated) — no lockout
```
Then insert from_seat/from_lineage/author_seat/author_lineage from those derived values, not raw body. This mirrors _trusted_seat usage in the other four routes and closes Q1. The dispatch-on-behalf exception (control sending a worker's proposal) is exactly the spec's §3 narrow, coordinator-gated case — implement it as a registry role flag, not an open default.

## Re-review path
Once send is migrated, this is a SIGN-OFF: the core + the other four routes are already correct, and send is the last identity-writing route. I did not send a kind=signoff row for KEYS-2 (verdict is REJECT). I'll sign off on the re-submit.

## Persistence
Verified without deploying: read all three files via read_file, the spec via read_repo, checked the repo for staged plaintext keys via read_repo (404 = none). Could not exercise authenticate_identity live (no per-identity key issued + deploy is control's) — validated by reading the registry/compare logic and tracing each route's identity source in code. Said what I tried.
