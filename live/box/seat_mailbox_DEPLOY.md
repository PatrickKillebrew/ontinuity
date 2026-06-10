# Seat Mailbox — deploy runbook

Box-side module: `seat_mailbox.py` (Flask blueprint, mirrors file_server.py's scoped-op + ops-ledger pattern).
Reached by sandbox seats via the relay-courier (/diag/op/mailbox_*).

## Order (each box step operator-gated, one at a time)
1. Place `seat_mailbox.py` in `/opt/ontinuity/` (same dir as file_server.py).
2. Register the blueprint in file_server.py: after `app.register_blueprint(db_blueprint)`, add
   `from seat_mailbox import seat_mailbox_bp; app.register_blueprint(seat_mailbox_bp)`.
   (This is the ONE splice — once the courier can reach /write, future box edits are hands-free.)
3. Restart: the table self-creates on import (_mailbox_init).
4. Engine: add the five mailbox ops to OP_ALLOWED in app.py and deploy (operator sign-off):
   OP_ALLOWED = {"read_journal","restart_workspace","register_egress",
                 "mailbox_send","mailbox_fetch","mailbox_ack","mailbox_peek","mailbox_reclaim"}
5. Smoke test through the courier: mailbox_send -> mailbox_peek round-trip.

## Schema (self-creating)
seat_mailbox: msg_id, from_seat, from_lineage, to_seat (name|role|broadcast), kind, block_id,
ref (corpus pointer), depends_on, body, status (queued|claimed|done|expired),
created_at, claimed_at, claimed_by, lease_until, done_at, reply_to.

## Properties (tested, test_mailbox.py)
- diag-key gated (X-Diag-Key, same as scoped ops)
- atomic claim (BEGIN IMMEDIATE; two seats never claim the same msg)
- lease + reclaim (un-acked claim returns to queue after MAILBOX_LEASE_SECONDS, default 900)
- ack-with-reply (reply routed back to original sender)
- ops-ledger dual-end logged (same audit spine as every scoped op)
- corpus is source of truth: mailbox carries coordination + ref pointers, never the canonical result
