# CONTROL_HANDOFF — next-seat boot target
Last updated: 2026-06-15 (morning), after the seed_tenant close. This file states the SINGLE next action so a fresh control seat runs the open ritual onto a clear target instead of re-deriving state. Run the OPEN RITUAL (OPERATING_MANUAL) first: orient from the corpus, do not reason from memory.

## STEP 0 — credentials (control seat)
Read the provisioned credential file in the sandbox (LLaves in the Claude project) — diag key, Railway project token, GitHub PAT(s), mailbox key. Never fabricate; if absent, ask the operator. Out-of-band only; never commit to the public repo.

## SINGLE NEXT ACTION
The SHS-Wasserman build day. Nothing below is gated on infrastructure — Katie is seeded, the tenant path is live, the manuals are current. The work is the build, in this dependency order (full detail: private repo ontinuity-intake-data, projects/shs-wasserman/ROADMAP.md):
1. P0 — Katie's sanitizer/de-identifier, as PLAIN DETERMINISTIC CODE (no model; her export has stable columns; deterministic beats probabilistic for an auditable guarantee). Gates everything: she can't hand over data until it exists. Build parameterized (columns declared via checklist) so it works the moment her sheet arrives. Spec in projects/shs-wasserman/mini_corpus.md.
2. P1 — Katie's materials once sanitized (Google Sheet = real field schema; schedule export). Map columns to the matcher; flag absent fields (forward availability, structured service area) — those the intake + heartbeat must supply.
3. P2 — two-way SMS loop (send + inbound webhook + first-valid-YES arbitration). Parallel to P0/P1; needs only a trial number.
4. P3 — A2P 10DLC registration (start early, ~1-3wk wait, fire-and-forget).
5. P4 — matcher ranking on her real fields.
PARALLEL human track: coffee with David (operator's father, investor, knows the franchise agreements + consultant network). Printable question doc delivered: projects/shs-wasserman/FOR_DAVID_franchise_questions.docx. Katie's asks: FOR_KATIE_tomorrow.docx. The one question that decides the wider-network path: is reaching the other ~125 SHS partners gated by ONE approved-vendor decision at corporate (who decides?), or owner-by-owner?

## STATE AT THIS HANDOFF
- Katie Wasserman seeded as first client tenant (user 07f75d61 / project eecb5348 "SHS Emergency Shift-Coverage Tool"), confirmed in the live DB.
- seed_tenant op LIVE on box + engine, in both manuals (17-op allowlist), in punch-list DONE. Future tenants are hands-free via /diag/op/seed_tenant.
- Engine idle. Hetzner Object-Storage outage (hel1/fsn1) still open but IRRELEVANT to operation (it's Object Storage, not the VPS; the VPS only accepts the Railway relay — direct :5001 timeout from a sandbox is firewall-by-design, NOT a dead box).
- DB BACKUP still UNBUILT (the last single-homed risk): only the live ontinuity.db on the VPS is at risk if the box is lost; everything else is on GitHub. Set up dump-to-private-repo + laptop copy + test-restore when convenient (an on-the-box task). Tracked in projects/shs-wasserman/ROADMAP.md Track A.

## STANDING LESSON (read before declaring any blocker)
This morning control twice declared an EXTERNAL blocker (Hetzner outage, then Railway egress throttle) without grounding in the corpus — same shape as the prior VPS-down miscall. Both real causes were INTERNAL and corpus-documented: (1) the relay-survives-firewall access pattern; (2) a new box op needs write_file-to-BOX-DISK + restart, NOT just a repo commit (manual line 122). RULE: when something "can't" be done, re-ground in the manual/corpus and verify ACTUAL state before declaring a blocker. The retrieval machinery is reliable; the only failure is not reaching for it.
