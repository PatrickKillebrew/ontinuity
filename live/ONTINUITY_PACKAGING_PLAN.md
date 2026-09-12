# ONTINUITY — PACKAGING PLAN
*Derived entirely from the Master System Map. The test of the mapping: this plan should reach
conclusions the corpus never stated in one place. Base image: MAIN=5640170 (pre-GPT engine + B5-P,
no B1), 19-op diag-key hands, boots oriented:true.*

═══════════════════════════════════════════════════════════════════
## THE CENTRAL DECISION THE MAP FORCES

The map surfaced something the corpus never says in one place: **there are TWO products hiding in
Ontinuity, at two different weights, and they should ship in sequence — not as one thing.**

- **PRODUCT 1 — The Corpus Discipline** (project-corpus-standard/). Zero-install. A folder + two rituals.
  Delivers the MEMORY value (well-documented, continuous, grounded) with NO engine, box, keys, or cost.
  Works with any model today. This is the "well-documented memory" the operator named as the good-first-day.
- **PRODUCT 2 — The Ontinuity Instance** (the engine). A per-operator Railway+VPS deployment that adds the
  ADVERSARIAL RELIABILITY and the AUTOMATED PIPELINE on top of the memory. This is what the operator runs.

The strategic error to avoid (the one GPT made): trying to ship Product 2 first. The map shows Product 1
is done and shippable NOW; Product 2 has exactly one unbuilt seam. Ship 1, then 2.

═══════════════════════════════════════════════════════════════════
## PRODUCT 1 — THE CORPUS DISCIPLINE  (shippable now, ~0 build)

**What it is:** the project-corpus-standard/ folder (6 templates) + README opener + close ritual.
**Who it's for:** the BIL/Cornel-type user who wants memory continuity, not infrastructure.
**Value on day one:** ends session 1 with a structured record; session 2 continues instead of restarting.
**Install:** copy the template folder to Drive (Gemini) or a git repo (Claude/ChatGPT); fill
PROBLEM_DEFINITION first (own words), CURRENT_STATE (what-exists + single-next-action); run the rituals.

**Build work required: essentially none.** It exists at project-corpus-standard/. Packaging tasks:
1. Extract project-corpus-standard/ into its own distributable (a zip / a public template repo).
2. Write the 3 platform quickstarts (Gemini exists; add Claude + ChatGPT one-pagers — trivial).
3. Optional: a landing page (the website already has the concept papers).

**This is the wedge.** It costs nothing to run, proves the core value (memory-not-recall), and every user
who outgrows it is a warm lead for Product 2. It also de-risks: real users exercise the discipline before
any engine is provisioned for them.

═══════════════════════════════════════════════════════════════════
## PRODUCT 2 — THE ONTINUITY INSTANCE  (per-operator engine)

### What each operator gets (from the map's infrastructure section):
- ONE Railway project (2 services: web=MAIN engine, ontinuity-farm=FARM worker engine)
- ONE Hetzner box (gunicorn :5001, the workspace + courier + mailbox)
- Their own corpus git repo
- Their own model API keys in FIVE role slots (model_a/b/c/projenius/parietal), with B ≠ A lineage
- Their own diag key (generated at provision, never in the boot packet)

### The base image to reproduce: commit 5640170 (pre-GPT + B5-P, no B1). Proven: boots oriented:true,
19-op diag-key hands, memory persists, auto-provisions user+project on first session.

### PROVISIONING SEQUENCE (per operator) — derived from the map:
1. **Fork the corpus repo** (or clone the template repo) into the operator's GitHub. This is THEIR corpus.
2. **Deploy the engine to Railway** — 2 services from the repo at 5640170, with role-provider env vars
   (their keys) + a freshly generated diag key + INTAKE token if they'll use Mode A.
3. **Deploy the box to Hetzner** — the 6 box files (file_server, box_ops, seat_mailbox, db, +2) +
   gunicorn + ufw whitelist (box accepts ONLY the Railway relay — the firewall-by-design ingress gate).
4. **Wire the box's diag key + Railway token** into the box environment (for its own deploy hand).
5. **First boot** — the operator (or an IT person) runs the CONTROL_QUICKBOOT snippet; auto-provision
   creates their user + first project on the first session.

### THE ONE REAL BUILD ITEM before Product 2 is a clean product:
**The intake→Knowtext/mini-corpus bridge** (the only confirmed-open seam in the whole map). Today Mode A
captures intake data to JSON but does not seed the project's first Knowtext or the mini-corpus that
pipeline stages 2-4 hand off through. BUILD: a bridge that reads the captured WORKSPACE_STATE and writes
(a) the project's first Knowtext version and (b) the mini-corpus seed. Bounded, well-specified. Mode B
(direct session) needs NO new build — it's fully live.

### PACKAGING CLEANUP (from the map's repo-hygiene findings) — exclude before shipping:
- **ODS files** (ontinuity_loop.py, ods_phase1_v5.py, camera_cte.py, mission_state.py, battery.json,
  live/sessions/*.txt) — a different project (autonomous driving) sharing the repo.
- **B1 machinery** (capability_auth.py, trusted_deploy.py, all B1 specs + test suites, both B1 manifests,
  the B1 worker docs) — discarded; keep in the bundle for reference, exclude from the product.
- **Retired stubs** (laptop_seat.py).
- **Roll the WORKER docs back** to pre-GPT (they describe the discarded B1 admission flow — a new user
  handed them reads about a system they don't have). Same fix already applied to the manual/gate.

═══════════════════════════════════════════════════════════════════
## THE CREDIBILITY / EXPLANATION LAYER (from BOUNDARY_GATE_PRIMITIVE + the papers)

When explaining Ontinuity to a collaborator/investor/employer, the map gives the spine:
**"Gate and prove, not trust and monitor."** One primitive — a checkpoint at a trust boundary that
defaults to NO until a safety property is proven — appears in Synapse (10 yrs ago), Rust (compile-time),
and Ontinuity (the contract gate). The cross-vendor succession proof (GPT inherited Control through the
corpus + hands, no engine rewrite) is the operational proof that it's model-agnostic infrastructure, not
a Claude trick. The website's 18 concept papers are the education layer already built.

═══════════════════════════════════════════════════════════════════
## RECOMMENDED SEQUENCE

1. **Ship Product 1 now** (extract corpus-standard, 3 quickstarts, optional landing). Get BIL/Cornel/Katie
   using the memory discipline. Near-zero cost, near-zero build. Real usage = validation + warm leads.
2. **Build the one seam** (intake→Knowtext bridge) so Mode A is automated end-to-end.
3. **Retrieve + update PROVISIONING_RUNBOOK.md** (private repo) to the recovered 5640170 state; validate
   by standing up ONE fresh instance (the operator's own Gemini test, per the July-20 plan).
4. **Package Product 2** — the reproducible per-operator instance, cleaned of ODS/B1/stubs, worker docs
   rolled back. First real external install = the outside-operator transfer test (Cornel, his own Railway+VPS).
5. **The insight layer + full automation** are year-two, on top of accumulated per-operator corpora.

═══════════════════════════════════════════════════════════════════
## WHAT THE MAP PROVED (the test result)

The map DID enable conclusions the corpus never stated in one place:
- Ontinuity is TWO products at two weights, and they should ship in sequence (never stated anywhere).
- Product 1 is done and shippable now (the corpus-standard folder was buried as one directory).
- Product 2 has exactly ONE unbuilt seam (the intake bridge) — everything else is built or is config.
- The per-individual-instance model dissolves the security items B1 was built to solve.
- The repo contains 3 things to exclude (ODS, B1, stubs) that no single doc flags together.
This is synthesis, not transcription. The mapping earned its cost.
