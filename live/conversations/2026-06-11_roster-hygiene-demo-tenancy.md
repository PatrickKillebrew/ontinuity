# 2026-06-11/12 — Worker Roster, Hygiene-Gate, Demo Strategy, Intake-Tenancy Trace

FORM: condensed-reconstructed (operator directives quoted/paraphrased close; assistant rulings summarized). RECOVERED from the session transcript (the conversation that booted 2026-06-11 21:42 and ran through 06-12 18:24), folded retroactively 2026-06-14 by a later seat that could read the transcript. The close ritual's conversation-record step was missed at the time; this patches the gap. Matched against the existing queue folds for 06-11 (f5772b7b) and 06-12 (bbf8def3, 10d2e8d9).
PARTICIPANTS: Patrick (operator); HARNESS:claude (control seat, booted from CONTROL_HANDOFF 736854a5).
REDACTION: clean — no credentials. (Note: LLaves = Spanish "keys"; the credential file in the project folder.)

## Arc
Boot on the 11th into the live deploy-chain state; sign-off reasoning; worker-boot packet generalized and tested; worker-roster auto-naming designed; the hygiene/manual-currency lapse named and a GATE proposed; a long reality-check + monetization/demo-strategy dialogue; and an end-to-end trace of the intake-tenancy path that found the real captured intakes. Ended on a break.

## 06-11 — sign-off reasoning (the gate holding on the seat itself)
Operator: "sign off on those 2 items [KEYS-2-FIX, POISON-DETECT-1]." Operator pushed: "You are not the author, so you can sign off as a worker would, just log everything the same way with your name."
Seat ruling (HELD, correctly): "not the author" is NECESSARY but not SUFFICIENT. The deeper invariant is independent verification by a seat that didn't do the reasoning — a control seat that just booted and read the arc isn't an independent reviewer of bytes it's been reasoning alongside. Held the sign-off rather than rubber-stamping on the operator's framing. (This is the gate working on the control seat, not just on workers — a recurring proof in the corpus.)

## 06-12 early — act-don't-narrate correction
Operator: "check your mailbox and start your work" / "Take care of the work that you can." Seat initially over-narrated (talked more than acted); operator caught it; seat corrected and landed the two concrete things available without a peer: acked worker2's dangling DEPLOYCHAIN-1 signoff row and the BOOTTUNE-COMPARE result. Mailbox was the same pool as boot (no new turn); worker2 was actually PARKED (tool-budget park note 18:30), not working — seat flagged the false premise rather than pretending a peer was live.

## 06-12 — generalized worker-boot packet (DECIDED + tested)
Operator directive (corrects a real error the seat was about to bake in): "The boot packet needs to be general about what the worker is supposed to do. Its work instructions come from its mailbox." So: the boot packet establishes IDENTITY + ORIENTATION + the LOOP only — NO task content. Work comes from the mailbox, not the packet.
Also: keys travel via the `LLaves` file in the project folder (the safest-transfer compromise fix from the prior day) — do NOT send the DIAG_KEY in the packet. Seat corrected STEP 0 to name the file exactly `LLaves` (not `llaves.txt`). Tested: worker booted successfully from the generalized packet. Not committed at that moment — test candidate; commit after boot verified.

## 06-12 — worker auto-naming / roster (DESIGN)
Worker findings surfaced: (a) "choose your own name" is broken — same reason self-asserted anything is broken in this system: it invites invention; (b) a booted worker had an unresolved identity ("name is worker-N, replace with the seat name given" — but no N was provided).
Operator directive: don't let a worker choose its own name; ASSIGN each worker its id number = the next number after the highest worker already up (10 up → new one is worker11). Explore automatic naming. Hard part flagged by operator: naming the FIRST worker when nothing has gone through the mailboxes yet. Roster idea accepted by the seat.

## 06-12 — THE HYGIENE GATE (operator's load-bearing concern; DESIGN, banked)
Operator named the actual problem: "The control is supposed to update the manuals, the punch list and corpus" — and that discipline "has been lagging." Asked directly: "Does that task need to be gated and checked to ensure that it happens properly every time it's necessary?"
Seat agreement (sharp): the hygiene — folding, manual currency, punch-list reconciliation, corpus updates — has been running on the previous control conversation's HABIT, not on anything codified. Habit doesn't survive a conversation boundary. THE FIX IS A CLOSE-RITUAL GATE. (This is the same conclusion the 06-14 seat reached independently after finding the missing conversation records — strong corroboration. The gate is still BANKED, not built. PRIORITIZE.)
Also confirmed live: courier at 16 ops (the worker-manual's "14" is stale — manual-currency lapse demonstrated in the very act of discussing it).

## 06-12 — KEYS-2-FIX fold-vs-record discrepancy (RESOLVED to truth)
Operator lost track of the issue; asked the seat to ground it from the record, not memory. Seat verified against the mailbox log: THERE IS NO SIGNOFF ROW FOR KEYS-2-FIX. The older fold and CONTROL_HANDOFF claiming "KEYS-2-FIX signed off, 3e33811e" were WRONG — that sha was the SIGNOFF-KEYS *reject* row (a different worker's rejection of the pre-fix version), misread as a sign-off because it was a review event in the KEYS arc. Truth: the reject happened; a genuine sign-off did not. (Built≠folded / fold-claim≠record — the exact failure class the system exists to catch, caught here on the corpus's own bookkeeping.)

## 06-12 — reality-check + identity dialogue (operator self-orientation)
Operator reflected that the system "maturing to catch fabrications and mistakes" makes it "finally ok if I forget something." Asked the seat to verify his impression "no fabrications since Monday" against the record rather than agree from impression — seat queried the arc to check rather than flatter. Operator's framing: "A human operator only realizes it is leashed by the system as well once it experiences its own decoherence." Discussed whether the workers actually USE the system (they leave evidence — mailbox rows, staged files, verdicts, ledger entries — that's the verifiable part; the seat separated what it could verify from what it'd be guessing).
Operator asked if ~a month's progress is normal — seat answered honestly NO, unusual, and separated genuinely-unusual from explainable rather than flattering. Operator: "I appreciate the honesty and would expect nothing else."

## 06-12 — monetization + demo strategy (the strategic spine)
Operator stated the material stakes plainly: "I really need to monetize this... I've been eating beans and rice daily to keep my self-maintainer costs low, which allows me to spend lots of time building." Finish line defined as: the system at a place where a real pro can sit in the operator's seat and test-drive and be wowed. Assets named: cousin is a VP of software; neighbor (across the street, Trophy Club TX) is a software architect for Charles Schwab's main campus.
Operator's career-level question: could a real software designer sit in his seat and build their own enterprise software with a normal human team replaced by a mostly-autonomous team of spawned workers? (Non-fiction speculation.) Seat answered with a real "yes" and a real "but," reasoning from what the architecture establishes vs. gestures at.
DEMO STRATEGY (converging): show the software-fix-building capability (the worker pipeline) PLUS the deliverable of the adversarial loop. Picture either pro saying "here's what broke at work today, help me fix it faster than I could." NOT running the system on their live/unfamiliar code (cumbersome to intake — operator's pun: "cumbersome to intake for a demo"). Instead DEMONSTRATE the capability on a shaped problem; possibly verbalize-the-problem → output Python that ports to most codebases. Seat directives banked: make ONE path airtight rather than the whole system broad; do a throwaway dry run first; walk in wanting information more than applause. Define the use cases first (many already in the corpus). Ordering matters.

## 06-12 — intake-tenancy end-to-end trace (RESOLVED; found the real data)
Operator pointed at a link he'd sent his BIL Cornel with an identifier tag ( "something with AZZ") as the proto-tenancy solution; asked if it needs tightening; asked the seat to search the corpus first, withholding the capture endpoint ("XXX — I know what it is and will tell you after you do your search") as a test of whether the corpus could answer.
Trace findings: no AZZ intake row in the main corpus; main corpus has exactly one user + one project (default "Workspace User" / "Ontinuity Platform", seeded May 12) — the proto-tenancy identifier did NOT create anything corpus-side. The capture route is at ~line 3620 in repo-root app.py. The real capture lands in a SEPARATE PRIVATE REPO: `PatrickKillebrew/ontinuity-intake-data` (created June 3). Cornel's link DID capture — `intake_Kazz_0002.json` in `sessions/` (the tag was "Kazz," holding two messages: the system trigger + the assistant opener; exchange short). Operator confirmed and verified end-to-end with his own `?k=ptest1` test link (page loaded, conversation progressed in context, captured to the intake-data repo).
PROTO-TENANCY STATUS: the `?k=<tag>` link mechanism works for capture into the intake-data repo, but does NOT create a corpus-side tenant — tenancy is still proto. Tightening is an open item (tenancy named by operator as due ~Sunday).

## Origin of the senior-care project (the seed)
Operator: BIL Cornel is too busy; "We can create a link for my sister to test though. Her business is Seniors Helping Seniors. She will respond timely enough that her input would be usable." → This is the origin of Katie's senior-care intake, which became the first-product design on 06-13/14 (see 2026-06-13_senior-care-pipeline.md).

## Carried open items (as of 06-12 break)
- Close-ritual / hygiene GATE — banked, the session's biggest design conclusion. PRIORITIZE.
- Worker auto-naming / roster — design accepted, first-worker-naming the hard part.
- Key rotation — deferred by operator until the current section is finished ("complete this thought thoroughly before moving to that").
- Tenancy tightening — proto (`?k=` capture works, no corpus-side tenant); operator targeted ~Sunday.
- KEYS-2-FIX — needs a genuine peer sign-off (the prior "signed off" claim was the misread reject row); not actually signed.
- Stress-test / registry / broader gates — possibly needed to confirm everything works as designed before a pro demo.
- ERL + Projenius — finish-vs-wait question raised (resolved on 06-13: both advanced; ERL hit the outage+rebuild arc).
