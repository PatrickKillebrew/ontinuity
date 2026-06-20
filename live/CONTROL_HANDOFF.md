# CONTROL HANDOFF — current state + the single next action
# Updated 2026-06-20 (evening) by control seat (claude.ai-chat:opus-4.8) at close.
# Orient from the corpus, not from memory. Read this, then PUNCH_LIST.md + the queue head.

## STATE AT CLOSE
- Engine healthy + idle. Box hands LIVE (courier 18-op allowlist confirmed by probe this shift).
- ROLE TABLE NOW CLEAN (was the day's reliability bug): A=external(claude-opus-4.8),
  B=cerebras/zai-glm-4.7, C=novita/meta-llama/llama-3.1-8b-instruct,
  PARIETAL=cerebras/gpt-oss-120b, PROJENIUS=novita/deepseek-v3-0324. Every role has an
  EXPLICIT, web-verified-live provider — none inherits the shared null-model fallback.
- Two stopped sessions this shift (2026-06-20_15-36-33 + the verification run); both were
  Researcher-seat laps by control, stopped intentionally (one on a self-referential contract
  criterion, see lesson below). Neither indicates a fault. Session count 320.
- Credentials: the LLaves keys are live and in use; the old "DARK until rotation" punch-list
  line is SUPERSEDED (operator accepts pre-public risk — no blast radius). Rotation is launch
  hygiene, not a current blocker.

## WHAT SHIPPED THIS SHIFT
- laptop_seat.py into version control (4af7b8b3) — closed the last single-homed-source gap.
- Dweller established to source: it is a recurring SESSION TYPE that ranks the queue by
  evidence and outputs the single defended next item — NOT software, NOT a punch-list build.
  Last lap 2026-06-06; stale. (corpus index unchanged; finding in punch list + conv record.)
- Parietal/Model-C provider fix — the day's reliability win — FIXED + VERIFIED LIVE. Root
  cause: roles with no explicit provider inherited a null-model Novita fallback that 404'd,
  hanging every Parietal-distilled close at finalizing:true (never writing). This was the
  demo-gating bug. Conversation record 00783ab9; punch list 839120e5.
- First Researcher-seat orientation lap for this control seat: the harness caught an imported
  ("June 7") date — a real priors-leak — and forced correction. Felt the recess from inside.

## STANDING LESSON (fold into any provider/config work)
Every in-cycle role MUST carry explicit *_URL/*_MODEL/*_API_KEY. A role configured "by
omission" silently inherits the shared PROVIDER_* fallback; if PROVIDER_MODEL is null it calls
the provider with no model string and 404s. "Configured by fallback" is a latent outage. Also:
when picking a provider model, WEB-VERIFY it is still live (Cerebras llama3.1-8b was deprecated
2026-05-27 — caught this shift before it re-broke anything).

## THE SINGLE NEXT ACTION
Operator's pick among the live primaries (unchanged from the documentation/build arc, now with
the reliability blocker cleared so a clean demo session is possible):
(a) EXPANDED SYNTHESIS PAPER — the keystone public doc; ground the live numbers first.
(b) THE SHELL OP — pattern-gated single box maintenance op (deny-then-allow), operator-wanted.
(c) SHS-WASSERMAN — the sanitizer is BUILT (found this shift on the laptop desktop:
    "shs cleaner\shs-cleaner", a Tauri app + standalone HTML fallback + synth fixtures); the
    P0 gate is cleared, so the client build can advance. Revenue track.
Confirm which with the operator on boot. NEW design item also open: Dweller-as-pool-surface
(wire the evidence-ranking session type to the worker pool's "which task next").
