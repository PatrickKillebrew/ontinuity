# ONTINUITY — THE INTAKE-MODE PRODUCT (SHS / SantaClean) — DEPTH-ARM
## The worked example of Mode A, and the concrete packaging template
*Depth-arm off ONTINUITY_MASTER_SYSTEM_MAP.md (Mode A / the intake front door) and the packaging plan.
Built from a full read of the SHS project corpus in the PRIVATE repo `projects/shs-wasserman/` (66 files):
the PM/memory layer, the shipped sanitizer (SantaClean), and the deterministic matcher. This is the ONLY
end-to-end proof Ontinuity ships a real product to a real customer — read it before any packaging work.
Reach the private repo via master map §22 (mint INTAKE_GITHUB_TOKEN from the Railway vault).*

═══════════════════════════════════════════════════════════════════
## 0. WHAT SHS IS (the one-line proof)
Katie Wasserman (operator's sister; Seniors Helping Seniors franchise, 29 clients / 35 caregivers / 3 TX
territories) filled out the intake questionnaire (session `Kshs`, 2026-06-12, 21 verbatim turns). Ontinuity
carried that intake across ~12 fresh-seat sessions to: a delivered proposal she called "perfect", a SHIPPED
Windows de-identifier (SantaClean / "Senior Care Data Cleaner", installed on her machine 2026-06-16), and a
built deterministic shift matcher. THE PRODUCT WORKS — this is the receipt. It also survived a hard mid-project
reversal (deterministic sanitizer shipped → shelved on third-party advice → rebuilt on a Presidio/GLiNER/k-anon
stack) WITHOUT losing the work, because the corpus carried it.

═══════════════════════════════════════════════════════════════════
## 1. WHAT KATIE ASKED FOR (the ground truth — SHS_PROBLEM_DEFINITION.md)
Built ONLY from her intake words; anything else is marked [INFERENCE] and is not ground truth. Her spec, verbatim:
"I would build my own system that had a search bar to put in the shift details and then tell me who would be a
match. Then... automatically send a text and email asking them if they want the shift. They would be able to
accept... Then the system would automatically update the schedule, and send the clients careplan to the caregiver."
- The problem: a caregiver calls out 1-2x/week; finding a qualified, in-range, available replacement takes her
  1-4 hours by hand; an unfilled personal-care shift ≈ $140 lost + a care gap.
- Her manual match, her order: (1) care level the client needs, (2) distance, (3) won't exceed 40 hrs → then call.
- "Automatically" appears 3× — she wants the work DONE FOR HER. (This is the SAME lesson as the Ontinuity
  product: the user does not do the mechanical work by hand. A tool that makes her do the matching faster is
  the wrong product.)
- Data lives in: ClearCare (client profiles, care plans, scheduling, billing) + a Google Sheet (caregiver
  availability, skills, hours). Care-level requirement ships as a STRUCTURED column ("Required Skills"), not
  buried in care-plan prose — which is why the "clinical prose must cross the membrane" fear was overblown.
- DISCIPLINE SPECIMEN: PROJECT_OUTLINE.md carries a `⚠ CORRECTION 2026-06-27` banner naming three drifts the
  design talk introduced ("client never crosses", "Katie hand-translates each time", "de-id is a requirement")
  and points back to the problem definition. This is the currency/grounding discipline working on a project corpus.

═══════════════════════════════════════════════════════════════════
## 2. THE FOUR INVARIANTS (PROJECT_OUTLINE — the cleanest "what makes it Ontinuity, not a script")
1. IDENTITY NEVER CROSSES. Two membranes — the SANITIZER (files, batch) and the SMS-BROKER (messages, live).
   The off-machine side reasons only in opaque tokens; if breached, nothing HIPAA-protected exists there because
   it was never there.
2. DETERMINISTIC WHERE STAKES ARE REAL. Matching and arbitration are plain code — provable, not probable. Models
   appear ONLY at the two human-language seams (prose availability, inbound SMS intent), never in the decision.
3. MODELS ARE LEASHED BY OUTPUT CONTRACT. Each model seam returns a frozen shape; a gate rejects off-contract
   output; ambiguity falls back to a human. Model for comprehension, code for consequence.
4. JUDGMENT IS ALWAYS ORIENTED AND RECORDED. Every escalation gives the human the verbatim trigger, the why, the
   decision, and the consequence — and that ruling becomes an audit-ledger row.
→ This is the boundary-gate primitive (master map §18) expressed at the application layer.

═══════════════════════════════════════════════════════════════════
## 3. THE TWO TOOLS (both run ON KATIE'S MACHINE — a correction the abstract map hid)
The maps described "three-layer identity topology" abstractly. Concretely there are TWO SEPARATE LOCAL TOOLS,
not a pipeline, and conflating them is an error the matcher's own docstring calls out:
- **SantaClean (the de-identifier / batch membrane)** — a BUILD-TIME tool. Katie runs it on her export; it
  produces a CLEANED file (real column shapes, no real identities) that she hands to the operator so the
  scheduler can be BUILT/TESTED against realistic data without the operator ever holding PHI. Only the CLEANED
  output leaves her machine.
- **The matcher (the production scheduler)** — runs LOCALLY on Katie's RAW roster, inside her trust boundary.
  It does NOT consume SantaClean's output — SantaClean coarsens City to "[location removed]" and strips shift
  times, the exact fields the area/time filters join on, so feeding it sanitized data yields ZERO matches.
  The production tool uses real names/towns/times in place because nothing leaves her machine.
KEY (SHS_WRAPPER_ROADMAP, resolved 2026-06-27): the token-only constraint applies ONLY to the build-time
de-identifier output, NEVER to the production tool. The trust boundary is the edge of her computer.

═══════════════════════════════════════════════════════════════════
## 4. SANTACLEAN — the shipped de-identifier (the packaging TEMPLATE for any Ontinuity desktop tool)
SHIPPED TWICE, both real:
- **June (1.x):** Tauri v2 + Rust shell wrapping the airgapped HTML sanitizer, NSIS installer. Shipped to Katie
  2026-06-16 (SHIP_RECORD). Verified PASS on both her real file shapes, 0 residual identifiers, in the binary.
- **Going-forward (2.x):** a Python + ML stack (Presidio + GLiNER ensemble detection, W2 encrypted mapping,
  W3 k-anonymity) — a DIFFERENT packaging problem than June (Tauri can't bundle a Python runtime + ~1GB models).
BUILD SPINE (SHS_WRAPPER_ROADMAP — W1–W4 all DONE 2026-07-01, with commits):
- W1 detection core (Presidio+GLiNER ensemble; two detectors must agree; excises names from Notes prose while
  keeping content — the upgrade over the old drop-the-column tool) — `shs_deid_w1.py` `9ba714da`.
- W2 persistent per-tenant mapping (Option B: stable token per person for life, AES-256-GCM at rest, DPAPI
  local key; the SINGLE most sensitive artifact, never leaves the machine) — `shs_mapping_store_w2.py` `b47e7abd`.
- W3 k-anonymity re-id check (PURE-PYTHON, not ARX → no JRE, whole stack one language). FINDING: k_min=1 on the
  small pool — k-anon can't be both safe and preserve matcher fields; escalated to operator + a HIPAA question
  (a real, recorded open risk) — `shs_reid_check_w3.py` `4c13fa9f`.
- W4 verify + append-only audit ledger orchestrating W1–W3 — `shs_verify_ledger_w4.py` `3af7263a`.
- W5 PACKAGING (design, grounded): PyInstaller `--onedir` (NOT onefile — onefile unpacks ~1GB per launch,
  trips SmartScreen) + pywebview shell reusing the June HTML UI + Inno Setup installer → `SeniorCareDataCleaner-
  Setup.exe` (AppVersion 2.0.0, per-user install, unsigned → SmartScreen "More info → Run anyway"). Models
  bundled (~750MB–1GB), no runtime egress. W6: an INDEPENDENT scanner scans the SOURCE for egress before ship,
  so the code must have no socket/network import anywhere in the detection/mapping path.
- BUILD HANDS: the `.exe` is built on the operator's Windows laptop (the box + sandbox are Linux) via the
  laptop-hands `/run` path (master map §23) — the 30-second-timeout detached-build pattern, BUILD.bat wrapper.
CARRIED-FORWARD non-technical-user safety design (engine-agnostic, survives the June→Python swap): two-level
airgap (no network code in page AND shell CSP `connect-src 'none'`); CLEAN file → native Save-As to Documents,
PRIVATE files (mapping key + audit ledger) → auto-written, no dialog, into a Desktop folder literally named
"SHS PRIVATE - Do Not Send" (physically separates the re-id key from the sendable file); nothing saved until a
button is clicked; deliver by Drive-link not email (Gmail blocks zipped .exe as a category policy).

═══════════════════════════════════════════════════════════════════
## 5. THE MATCHER — the deterministic differentiator (scheduler/matcher.py)
The wedge CareFinder/WellSky can't do: given a HYPOTHETICAL shift (no client record, no committed shift),
instantly answer "who on the roster could cover this?" Filters (plain code, no model): skills cover the shift
AND area reaches it AND free in the window AND hours remain; ranks; anything it can't decide cleanly is surfaced
with trigger/why/decision/consequence, never guessed. Controlled skill vocabulary (HMKR/PAS/DEMENTIA/RN + aliases,
with constraint terms like "NO LIFTING" excluded) — a lookup, not a model. "A model here could hallucinate a
wrong match a WHERE clause never would."
KNOWN P2 landmine (SANITIZER_NOTES): cross-file token consistency — roster and schedule tokenized separately give
the same person different tokens, breaking the schedule↔roster join; W2's shared persistent mapping is the fix.

═══════════════════════════════════════════════════════════════════
## 6. THE COMMERCIAL MODEL (FROZEN_PRODUCT_SHAPE_2026-07-08) — the map had nothing on this
- PRODUCT SHAPE: a packaged, downloadable desktop tool, licensed MONTHLY, runs LOCALLY + OFFLINE on each SHS
  owner's own machine against their own data. NOT hosted, NOT a service, NOT multi-tenant. One owner, one machine.
  → INDEPENDENTLY THE SAME CONCLUSION the Ontinuity packaging project reached (per-individual instances, not
  shared hosting). Two separate products converged on it. Strong corroboration for the packaging decision.
- CAPABILITY FRAMING (keep NARROW): only the hypothetical/what-if match — never "matching" generally, because
  WellSky already does certified caregiver↔client matching; the broad framing collides with a certified incumbent.
- LICENSING (resolved): a cryptographically SIGNED expiry-key file, checked offline against the local clock on
  launch; past expiry → refuses to run + shows a plain-language renewal path. Renewal = a NEW KEY (drop-in / one
  line), the app STAYS INSTALLED — no reinstall, no repeat SmartScreen, no model reload. Non-payment self-enforces
  (stop issuing keys). REJECTED: self-deleting monthly (reproduces the SmartScreen/model-load friction, reads as
  malware, churns faster than non-payment); heartbeat licensing (sacrifices the "nothing leaves this machine"
  claim, the actual privacy differentiator). ACCEPTED honest weakness: clock-rollback defeats it and there's no
  telemetry — not overbuilt because the customer base is small home-care owners, not pirates.
- GTM: the SHS franchise "Item 8" (unapproved-software restriction) is real; aim bottom-up demand at getting the
  tool APPROVED by the franchisor (PE-owned), which reaches all ~125 owners at once, not at bypassing approval.
  Katie estimated ~50 customers via her network; this tool is the "wow" that unlocks the wider SHS network + AZZ.

═══════════════════════════════════════════════════════════════════
## 7. HOW A NEW INTAKE-MODE TENANT IS SEEDED (seed_tenant.py — the real one)
`projects/shs-wasserman/seed_tenant.py` runs ON the box against ontinuity.db: idempotency guard → `insert_user`
(display_name, plan="pro", feature_flags {client_tenant, sanitizer_required}) → `insert_project`. STRUCTURAL seed
only; the doc is explicit: do NOT route the client's live data through the shared engine until engine-URL auth
gating closes — "the sanitizer design means we hold no identity meanwhile." Katie = the proven run (user seeded,
project "SHS Emergency Shift-Coverage Tool"). This is why the live DB shows her as user #2.

═══════════════════════════════════════════════════════════════════
## 8. WHAT SHS TEACHES PACKAGING (the synthesis)
- The intake-mode product and the design-mode product are DIFFERENT deliverables but reach the SAME shape:
  local, offline, per-individual, the user does no mechanical work by hand. SHS is the empirical confirmation
  of the per-individual-instance packaging decision.
- The desktop-tool packaging TEMPLATE is worked and shipped: PyInstaller onedir + local shell + Inno Setup,
  built on a Windows laptop via the /run hands, delivered by Drive-link, licensed by signed offline expiry-key,
  with the non-technical-user safety design as a checklist. Any Ontinuity desktop deliverable reuses this.
- The membrane pattern (SantaClean) is reusable: it became the generic de-identifier (`sanitizer/generic/`,
  "SANTA CLEAN") with its own gazetteer + medical lexicon — a productizable component beyond SHS.
- OPEN/HONEST (not hidden): the W3 k-anon small-pool finding (safe-vs-useful tension) is a real recorded risk
  with a HIPAA question outstanding; live-data routing waits on engine auth gating; A2P 10DLC SMS registration
  not started. These are the genuine remaining unknowns for the intake-mode product — none are design gaps.
