# FARMFIX-VERIFY — corrected diagnosis of the Cerebras/Novita 404
Block: FARMFIX-VERIFY | Seat: worker2 | Lineage: claude:opus-4.8 | Verify-and-correct (peer review of FARMFIX-1)
Grounding: live model_registry + sessions corpus, live /diag/egress, and live/agent_queue.md (read via courier). Inference labeled.

## Verdict on FARMFIX-1: REJECT (control's catch is correct)
FARMFIX-1 proposed FARM model_c meta-llama/llama-3.1-8b-instruct -> bare llama3.1-8b. Control checked live FARM config: MODEL_C_URL=Novita, MODEL_C_API_KEY=Novita. The prefixed string is CORRECT for Novita; the proposed change would point a Novita endpoint at a Cerebras-style string = a NEW 404. Do NOT change FARM Friction. CONFIRMED — and this traces to my own earlier POOLTEST-1 error: I read the recorded model_c string as wrong-for-Cerebras without checking that model_c's URL is Novita, not Cerebras. The string was never the bug; I matched a string to the wrong provider.

## Where the real 404 actually was: MAIN's Challenger (model_b), NOT FARM, NOT Friction
The record names it directly (live/agent_queue.md):
- L483 OPERATING NOTE: "MAIN Challenger is provider-dead on Novita (404) — fails adversarial close on MAIN until the Challenger model string/provider is fixed."
- L501 ROOT: "MAIN's Challenger had NO MODEL_B_* vars, so it inherited the shared Novita PROVIDER and died on a Novita 404." 
- L489 a live session closed status=incomplete_model_dead because the Challenger died on Novita 404 and never reviewed the close (Fix #4 correctly refused to certify).
So the mismatch was: MAIN Challenger (model_b) had no MODEL_B_URL/MODEL_B_MODEL of its own, fell through _vault_fallback (app.py L169-180) to the shared PROVIDER_URL=Novita, but the model string it carried was not served at that Novita endpoint for that role -> 404 at the adversarial close.

## Already fixed on the record (June 10 fold, L495-502) — verify, don't re-propose
Operator already corrected it via Railway variableUpsert on the MAIN web service:
- MODEL_B_URL  = https://api.cerebras.ai/v1/chat/completions
- MODEL_B_MODEL = zai-glm-4.7   (bare Cerebras string; registry confirms zai-glm-4.7 provider=custom/Z.ai, served on Cerebras; farm Researcher already used it, receipt #50)
- MODEL_B_API_KEY = existing CEREBRAS_KEY in MAIN's vault (no new key)
- UNCHANGED deliberately: PROVIDER_URL stays Novita (serves Friction + Parietal on MAIN); MODEL_A = external mailbox/Claude seat.
CONFIRMED WORKING (L506-509): the next MAIN session (2026-06-10_18-24-37) closed certified COMPLETE, 7 cycles/10 turns, Cerebras GLM-4.7 Challenger, lineage-independent from the Novita-served Parietal. Clean before/after vs session 1 (Novita Challenger died -> incomplete_model_dead).

## Reconciling the line-112 FARM 404 (the block's starting point)
Line 112 is a SEPARATE, minor item: "one 404 mid-session on a farm model call (one string likely wrong for Cerebras)." FARM topology (L102) = all-Cerebras under a single PROVIDER env. FARM's recorded role strings (corpus, 263+4 sessions) are model_a zai-glm-4.7, model_b/parietal/projenius gpt-oss-120b, model_c meta-llama/llama-3.1-8b-instruct. 
INFERENCE (labeled, can't read FARM live env): on FARM, model_c's prefixed string is the candidate for the line-112 one-off ONLY IF FARM model_c also inherits the all-Cerebras PROVIDER_URL. But the block states FARM MODEL_C_URL=Novita explicitly — meaning FARM Friction has its OWN Novita override and does NOT inherit the Cerebras PROVIDER. If that live config is current, FARM Friction is correctly Novita+prefixed and is NOT the line-112 404 either. That leaves the line-112 one-off most likely a transient (retry-recoverable, per L483 "retry often recovers") rather than a standing misconfig — the standing 404 was MAIN model_b, now fixed. I cannot fully close line-112 without FARM's live env; flagging the boundary rather than asserting.

## Corrected fix summary (what was actually needed vs FARMFIX-1)
- WRONG (FARMFIX-1): change FARM model_c string. Would break a working Novita role.
- RIGHT (already applied June 10): give MAIN model_b its own Cerebras URL+bare string+Cerebras key, so it stops inheriting Novita and stops 404-ing at the adversarial close. Role=Challenger/model_b; vars=MODEL_B_URL/MODEL_B_MODEL/MODEL_B_API_KEY; old=inherited PROVIDER_URL=Novita with no own model -> new=Cerebras + zai-glm-4.7 + CEREBRAS_KEY. String matches provider: zai-glm-4.7 is the bare Cerebras form. VERIFIED by the certified-complete session that followed.
- No action proposed on FARM Friction (correctly Novita).

## Method note / persistence
- session_executions has no provider-error capture (queried for 404/fail: 0 rows) — the 404s live in the queue's operating notes, not the exec log. Worth a follow-on: capture provider HTTP status into session_executions.detail so 404s are queryable, not just narrated.
- /diag/egress on THIS engine returned a live 404 (provider_status 404, provider_url Novita, provider_model "claude.ai-chat:claude-opus-4.8") — but that is the MAIN instance's egress PROBE using a bad MODEL_A_MODEL env value (my lineage string, not a real model); it is a diagnostic-probe artifact, NOT the FARM session 404, and I did not conflate them.
- Could not read FARM live env (Railway secrets); used corpus strings + the queue's explicit config folds instead. Said so.
- Read-only verify block: no code changed, no deploy.
