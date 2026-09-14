# MUSEUM — discarded directions, preserved as specimens

Ontinuity documents failures so they are not repeated. Nothing here is on the live path; nothing here is
deleted. Each specimen keeps its original repository paths under its own directory so it can be read,
compared, or (deliberately) revived. Full lineage is in git history and in the preservation bundle
`e15f5f46` (commits `693435a..0ef62d7`).

## b1/ — the "operator-approved capability admission" direction (2026-09-06..11, GPT-driven)
WHAT: `capability_auth.py`, `live/box/trusted_deploy.py`, the v2 HTTPS transport (`ontinuity_https.sh`,
`ONTINUITY_ENDPOINTS.conf`, `specs/ontinuity_https_protocol.md`), the trusted exact-commit deploy
protocol, both B1 manifests, the B1 verifier, the iPad private-transfer evidence, and nine test suites.
WHY DISCARDED: it built multi-tenant AUTHORIZATION machinery (signed capabilities, admission panel,
two-party deploy tuples, HTTP 428 envelopes) for a product whose model is PER-INDIVIDUAL instances —
each operator owns their own engine, box, repo, and key, so the untrusted-seats-sharing-one-engine threat
it defends against does not exist. In the process it replaced the direct diag-key hands the operator's
own boot depends on, and left the corpus's Control/Worker packets describing a system the live engine
did not run. LESSON: confirm the product model before building isolation/authorization. The one hygiene
lesson kept: per-instance keys, never in the boot packet. Small hardening lost with the revert
(read_repo path validation, atomic private writes, mailbox field validation) is tracked in
`live/PUNCH_LIST.md` as "B1 hardening salvage" — re-apply as bounded fixes on the pre-GPT base, never by
restoring these modules.

## b-blocks/ — the "Ontinuity 1.0 completion phase" plan (2026-09-03, GPT-driven)
WHAT: `ONTINUITY_1_0_BOARD.md` (release board) and `ONTINUITY_1_0_COMPLETION_PLAN.md`.
WHY HERE: this was GPT's dependency-ordered plan (B0..B10) that led to B1. Its B0 baseline
(`live/baselines/`, `live/ONTINUITY_1_0_BASELINE.md`) and B5-P evidence layer were KEPT on the live path
as evidence and feature respectively; the plan itself is superseded by the July-19 packaging roadmap in the
private repo (`projects/the-package/ROADMAP.md`). Retained for provenance only.
