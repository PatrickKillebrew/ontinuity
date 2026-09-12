# 2026-09-12 — Pre-GPT recovery, full-corpus mapping, and the two-product packaging decision

FORM: condensed decision-record per live/conversations/CONVENTION.md. Operator directives and rulings
quoted/paraphrased close; agent narration summarized. REDACTION: clean — no keys, tokens, or IPs reproduced.
PARTICIPANTS: Patrick (operator); claude.ai-chat:claude-opus-4.8 (control seat, working from the sandbox
via the diag-key courier and the Railway GraphQL deploy path).
LINEAGE: MAIN restored to 5640170 (pre-GPT engine + B5-P, no B1); FARM to f9696c49; box gate reconciled to
19 ops; produced ONTINUITY_MASTER_SYSTEM_MAP.md, ONTINUITY_COVERAGE_CHECKLIST.txt, ONTINUITY_PACKAGING_PLAN.md,
ONTINUITY_PRE-GPT_RECOVERY_PLAN.md, ONTINUITY_GPT_WORK_EVALUATION.md.

## ARC
The operator returned after a difficult week: a prior GPT-driven "B-block" completion phase (Sept 3–11)
had left MAIN running B1 capability/admission code, which BROKE the direct diag-key hands the operator's
own boot depends on. The session (1) recovered the system to its pre-GPT state as a HYBRID (pre-GPT engine
+ the one genuinely valuable GPT addition, B5-P evidence preservation), (2) mapped the ENTIRE 252-file
corpus into a single durable reference to finally answer "what is Ontinuity and how do we package it,"
and (3) reached a two-product packaging decision the corpus had never stated in one place.

## RECOVERY (executed + verified)
- Diagnosed: MAIN on B1 (0ef62d7) rejected the diag key ("malformed capability"); FARM had never migrated.
  The B0 baseline (2026-09-04) proved MAIN/FARM ran DIFFERENT pre-GPT commits — they were never identical.
- True pre-GPT MAIN engine = 9a7eac2a (blob 3fcaaf31, 19-op diag-key). Verified in git before any deploy.
- Deploy mechanism recovered FROM THE CORPUS (CONTROL_HANDOFF "DEPLOY TOPOLOGY"): Railway GraphQL
  serviceInstanceDeploy, header Project-Access-Token (NOT Bearer), fixed project/env/service IDs.
- Restored MAIN → then, on the keep/discard evaluation, to 5640170 (= 9a7eac2a + B5-P, ZERO B1). FARM → f9696c49.
- Reconciled the box gate + manual to 19 ops (B1 had bumped them to 20). A full Control boot returns
  oriented:true, all 6 checks + all 4 mechanics invariants. Data intact (328 sessions). B1 preserved in
  bundle e15f5f46, discarded from the live path.

## RULINGS / DIRECTIVES (operator)
- "Everything needed system-infrastructure-wise is documented in the corpus" — repeatedly redirected the
  seat from inventing solutions to READING the record. The deploy path, the true pre-GPT commit, and the
  box-install-vs-commit rule were all already written down; the failure each time was not reaching for them.
- On the GPT week: keep the genuine value, discard the rest. Evaluation (commit-by-commit): KEEP B5-P
  (auditability spine), db.py transactions, control_loop hardening, release_baseline.py, the B0 baseline,
  the cross-vendor succession record. RESTORE ipad_keyboard (GPT had deleted it). DISCARD the B1
  authorization machinery (capability/admission/trusted-deploy) — wrong for a single-operator system.
  The prior fix-specs (cyclenum/query_guard/deploy_drift/farmfix/erl/signoff) are PRE-GPT — already the
  operator's, already in the foundation. Net: ~30% of the GPT week was real value; most of it additive.
- On mapping: "finish mapping the skeleton and its details before we try to package anything." And the
  anti-drift method the operator named and the seat adopted: TAKE NOTES AND MOVE ON — do not solve a thing
  the moment it's found; note it, flag the concern, keep crawling. This held across all 252 files.
- On not prejudging: "Don't prejudge what a stage will reveal. Things get missed when you prejudge... you
  set an expectation before you evaluate something and that bounds how much effort you put in." Directly
  corrected the seat's plan to skim the conversation records; reading them fully surfaced the primary-source
  record of every architectural decision.
- On the map's worth: the test set was falsifiable — could the seat, from the map, WRITE THE PACKAGING PLAN
  and reach conclusions the corpus never stated? If not, the mapping was transcription and a waste.
- "Make doing this the right way obvious to a cold model with a different user" — the reason for this record.

## THE MAPPING (method + result)
Method: a file-coverage checklist (all 252 files) as the falsifiable "done" instrument, worked in 6 stages
by folder (core doctrine → prompts → specs → code → conversations+sessions → everything else), each file
flipped UNREAD → SUMMARIZED or READ-not-skeletal, load-bearing findings folded into ONE master map, running
count reported every stage. Reached 252/252, 0 unread. Then SFINAL resolved/confirmed every [OPEN] item and
traced both front-door flows end-to-end.

Durable findings (see ONTINUITY_MASTER_SYSTEM_MAP.md for the full 22-section map):
- ONTINUITY HAS TWO FRONT DOORS: Mode A (intake website → 4-phase discovery → solution pipeline; the ONLY
  door to that mode) and Mode B (direct session — operator + seat doing design/build with memory continuity).
- MEMORY IS A LAYERED SYSTEM, not just Knowtext: git corpus + a 24-table relational DB (live: 357
  knowtext_versions, 328 sessions, 3 projects, 2 users incl. Katie Wasserman) + Knowtext (the distilled
  7-field top layer, written by Projenius DISTILL at close). Retrieval-not-recall is mechanically enforced
  by the bootstrap gate.
- MEMORY-WRITING IS A MODEL ROLE (Projenius), not a script — a fresh install needs Projenius configured.
- provisioning IS built (seed_tenant, proven with Katie) and auto-provisioning fires on first session.
- The repo contains NON-Ontinuity code (ODS autonomous-driving files, retired stubs) to exclude when packaging.
- BOUNDARY_GATE_PRIMITIVE.md is the deepest "what Ontinuity is": one design primitive — gate and prove,
  not trust and monitor — across Synapse, Rust, and Ontinuity. The credibility spine.

## THE TWO-PRODUCT DECISION (the packaging conclusion — see ONTINUITY_PACKAGING_PLAN.md)
The map forced a distinction the corpus never stated in one place: THERE ARE TWO PRODUCTS AT TWO WEIGHTS.
- PRODUCT 1 — THE CORPUS DISCIPLINE (project-corpus-standard/): zero-install memory continuity. A folder +
  two rituals, works with any AI via that platform's NATIVE file access (Drive for Gemini, attached repo
  for Claude). NEEDS NO ENGINE/BOX/HANDS — because there is no sandbox-to-box firewall to cross; the USER
  reads and writes their own corpus. The hands exist only to let a firewalled sandbox seat reach a hosted
  box (Product 2's problem). Product 1's tradeoff: memory grounding is enforced by USER DISCIPLINE (the
  rituals), not mechanically. Shippable now, ~0 build. THE WEDGE.
- PRODUCT 2 — THE ONTINUITY INSTANCE (the engine): a per-operator Railway+VPS deployment (own box, own
  keys in 5 role slots with B≠A lineage, own diag key generated at provision, own corpus repo) that adds
  the adversarial reliability + automated pipeline ON TOP, and mechanically enforces retrieval-not-recall.
  Base image = 5640170. ONE real build item remains: the intake→Knowtext/mini-corpus bridge (Mode A's only
  unbuilt seam; Mode B is fully live). Per-individual instances dissolve the security items B1 was built for.
- SEQUENCE: ship Product 1 now → build the one seam → retrieve+update PROVISIONING_RUNBOOK.md (private repo)
  to the 5640170 state → package Product 2 → first external install (Cornel, own Railway+VPS) = the
  outside-operator transfer test.

## STATE LEFT
MAIN = 5640170 (pre-GPT + B5-P, no B1), FARM = f9696c49, 19-op diag-key hands, boots oriented:true, 328
sessions intact, memory persisting. B1 shelved (bundle + git). The master map, coverage checklist, and
packaging plan are the durable products of this session. Mode B is fully live; Mode A is live except the
one named bridge seam.

## CROSS-REFERENCE
Recovery deploys via Railway GraphQL (MAIN→9a7eac2a→5640170, FARM→f9696c49). Commits this session: manual
19-op rollback (c7ea00c), gate 19-op reconcile (fd613f7), B5-P engine + ipad restore (379ec0e), recovery
docs (d005532). Durable artifacts: ONTINUITY_MASTER_SYSTEM_MAP.md, ONTINUITY_COVERAGE_CHECKLIST.txt,
ONTINUITY_PACKAGING_PLAN.md. The map's own done-criteria check + both flow traces are in its §20 (SFINAL).

## ERRATA / FAILURES DOCUMENTED (museum specimens — preserved so the system does not rediscover them)
Per operator direction 2026-09-12: Ontinuity documents failures so they are not repeated. These are kept
in-record, NOT scrubbed.

**FAILURE 1 — the "two-product" misconclusion (control seat, this session).** The seat concluded Ontinuity
should ship as TWO products: a zero-install "corpus discipline" (Product 1) where THE USER manually runs
open/close rituals, commits files, and maintains ledgers by hand; and the engine (Product 2) "later." The
operator rejected this sharply and correctly: **a non-technical user must NEVER be expected to do these
technical things by hand. The mechanical, automatic enforcement of the rituals/writes/ledgers/grounding IS
the product — it is the magic of Ontinuity.** A folder-and-checklists discipline that depends on USER
discipline is not Ontinuity; it is a note-taking convention. The tell the seat missed: it has never once
been asked to have the OPERATOR write to the repo — in a working Ontinuity the SEAT does it through the
hands. CORRECTED UNDERSTANDING (operator, verbatim intent): "The user's discipline doesn't need an
Ontinuity; the fact that these things happen and are mechanically enforced is the magic of the system.
Ontinuity needs to do this work automatically." → There is ONE product: a per-operator instance that does
the retrieval, grounding, ritual, Knowtext writes, and ledger maintenance AUTOMATICALLY and MECHANICALLY,
invisibly to the user, who just talks. Packaging = giving each operator their own instance that runs all
this FOR them. project-corpus-standard/ is the SPEC of the discipline the engine automates — NOT a shippable
manual-labor product. FAILURE CLASS: proposing to offload the system's own mechanical work onto the user =
the inverse of what Ontinuity is for (cf. the recurring "comfortable-delegation" failure — routing work to
the human that the system should do itself, 2026-06-09/14).

**FAILURE 2 — the seat's recurring priors-over-corpus pattern, live this session.** Repeatedly the seat
reached for an invented answer when the corpus already held it: it nearly freestyled the close-ritual/fold
format instead of reading OPERATING_MANUAL's documented CONTROL-SEAT CLOSE RITUAL; it declared a 404 on the
private intake repo without first checking the token's actual scope; it proposed restoring MAIN "to match
FARM" before the B0 baseline proved they were never the same commit. Each was corrected by grounding in the
record. This is the SAME failure-class the whole corpus documents (recall-not-retrieval, wall-declaring,
assert-from-adjacent-layer). Preserved here as one more specimen: the fold/retrieval machinery is reliable;
the only gap is failing to reach for it.

## B1 — MUSEUM PIECE (discarded direction, files preserved)
The B1 "operator-approved capability admission" work (Sept 3–8, GPT-driven) is DISCARDED from the live path
but PRESERVED as a museum specimen of a failure-class: **over-building multi-tenant AUTHORIZATION machinery
for a system whose product model is per-INDIVIDUAL instances.** B1 correctly identified a real threat
(untrusted seats sharing one hosted engine) and solved it rigorously — but that threat does not exist under
the per-operator-instance model (each operator has their own box + key; nothing is shared). The capability/
admission/trusted-deploy apparatus made the operator's OWN single-operator system cumbersome (authorizing
themselves every action) and BROKE the direct diag-key hands the boot depends on. LESSON FOR THE NEXT SEAT:
before building isolation/authorization machinery, confirm the product model — per-individual instances
dissolve the multi-tenant-sharing threat that authorization machinery exists to solve. FILES PRESERVED
(accessible if ever needed): bundle e15f5f46; git commits 693435a..0ef62d7; capability_auth.py,
trusted_deploy.py, the B1 specs (trusted_deploy_protocol, signoff_*, per_identity_keys, gated_session_
substrate, ontinuity_https_protocol, scoped_operations_spec), both B1 manifests, and the B1 test suites.
The ONE B1 hygiene lesson worth keeping even for a single instance: per-instance credentials + never put
the key in the boot packet (already the LLaves/vault pattern).
