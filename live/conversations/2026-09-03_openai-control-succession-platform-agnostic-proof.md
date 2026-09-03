# OPENAI CONTROL SUCCESSION + PLATFORM-AGNOSTIC PROOF — 2026-09-03

**Form:** condensed decision-record. Operator rulings/directives quoted verbatim; connective narration condensed. Full-fidelity conversation remains operator-held in ChatGPT.

**Participants:** Patrick Killebrew (operator); `chatgpt-work:gpt-5.6-sol` (Control conversation and external Researcher occupant); `cerebras:gemma-4-31b` (Challenger); the standing Parietal and extraction roles configured on MAIN.

**Scope:** seat a non-Anthropic conversation as Control, orient it through Ontinuity's existing corpus and HTTPS hands, let it occupy the external Researcher seat in a real gated session, and determine whether the system's model/platform-agnostic claim survives contact with a different vendor and chat surface.

---

## WHY THIS SESSION HAPPENED

Corpus activity stopped near the end of July after the operator's working relationship with Anthropic's consumer models ceased to be productive. The system was not retired; the human-model working loop that maintained it had broken. The operator moved the Ontinuity project into ChatGPT, supplied the existing keyring through the project's file surface, and issued the standing instruction: **"Boot as a control conversation."**

The material question was not whether an OpenAI model could discuss Ontinuity. It was whether a fresh conversation, made by another company and running on another platform, could inherit the Control office through the existing record and hands without a rewrite of the engine.

The July 20 corpus had already settled the architecture: the consumer chat application is not the harness; the ENGINE is. Seating another model should be configuration plus a boot, not a new bridge. That was a design conclusion. This session tested it operationally.

## THE SUCCESSION TEST

The OpenAI conversation used the existing Control boot path rather than a newly authored OpenAI path. It retrieved the live operating record, reconciled the stale June handoff against the July 19 queue head, authenticated to the existing Railway HTTPS courier, and received the live 19-operation allowlist. No Ontinuity runtime component was rebuilt for ChatGPT.

What transferred across the vendor boundary was not hidden chat memory. It was the office:

- corpus-before-priors orientation;
- current-state reconstruction from handoff, punch list, queue, manual, paradigm, and rubric;
- scoped read/write/commit/mailbox hands through the existing courier;
- the distinction between Control and in-cycle seats;
- the external Researcher mailbox contract;
- the fail-closed adversarial gate;
- the prohibition on treating a model's confidence as system state.

The operator named the result accurately in conversation: **"I'm just glad that we were able to reproduce a working system on a platform other than Claude."**

The Control seat described the event as institutional succession: one intelligence left a position; another intelligence from another company inherited the office. That is stronger than an "AI memory" claim. Memory would mean recalling prior content. Succession means reconstructing authority, obligations, tools, current state, and limits well enough to continue operating the same institution.

## FIRST LAP — FAILURE PRESERVED, GATE WORKED

Session `2026-09-03_14-13-03` put ChatGPT into the external Researcher seat. The session did not complete. The configured Challenger was `cerebras:zai-glm-4.7`, which Cerebras no longer served; the provider returned 404.

The important result is what Ontinuity did next: it did not silently skip the dead judge, substitute the Researcher's own opinion, or certify the output. It failed closed. The session persisted as:

- status: `incomplete_model_dead`
- cycles: `3`
- recorded Challenger: `zai-glm-4.7`

That failure was diagnosable from the live cockpit/console and durable session record. It also disproved an initial Control inference that stopping an external session would leave no persisted record; the deployed engine wrote the incomplete session honestly.

## CONFIGURATION REPAIR — NO ARCHITECTURE CHANGE

The available Cerebras model list was checked against the live provider rather than guessed. It returned `gemma-4-31b` and `gpt-oss-120b`. To preserve the existing separation between Challenger and the `gpt-oss-120b` Parietal, Control changed only MAIN's `MODEL_B_MODEL` from the retired GLM identifier to `gemma-4-31b` through Railway's variable path. The readback verified the new value and the engine returned idle.

No code changed. No mailbox changed. No prompt changed. No new OpenAI adapter or MCP layer was introduced. This was the exact architectural claim under test: a seat/provider failure was repaired at the staffing layer.

## SECOND LAP — COMPLETE

Session `2026-09-03_14-35-29` ran the real loop:

1. The Parietal froze three judged criteria.
2. The engine posted a real `researcher_turn` to the external mailbox.
3. ChatGPT answered as Model A/Researcher.
4. `cerebras:gemma-4-31b` challenged the answer and found all three criteria complete.
5. ChatGPT requested `SESSION_END`.
6. The Challenger reviewed the close request and accepted it.
7. Work-product extraction completed.
8. The database persisted status `complete`, `2` cycles; the engine returned idle.

This was not role-play inside ChatGPT. The external answer crossed the HTTPS mailbox into the deployed Ontinuity engine and was evaluated by independently configured in-cycle roles. The gate that rejected the first lap certified the second.

## MONITORING SURFACE REDISCOVERED

The operator remembered the original live conversation window, public Researcher input, and Keys modal. A source read established that the current `app.py` and `templates/index.html` still contain the full Socket.IO cockpit, transcript, session controls, Researcher participation path, and `save_api_keys` modal flow. The cockpit is live at the Railway engine root; `ontinuity.org` now serves the static public site, which is why those controls appeared to have vanished.

Standing caution: the Keys modal writes process-global `runtime_configs`; those values outrank Railway role variables, and the last browser to save wins. It is therefore useful for diagnosis/manual staffing but dangerous as an unnoticed configuration race. During this test the operator monitored the Railway cockpit but did not use the modal to overwrite the verified role configuration.

## WHAT THIS PROVES — AND WHAT IT DOES NOT

**Proved in operation:**

- A ChatGPT Work conversation can inherit the Control role from the corpus.
- The existing HTTPS hands are sufficient for orientation and bounded operation from a non-Anthropic chat platform.
- The external Researcher mailbox accepts a non-Claude occupant without engine redesign.
- Provider seats remain replaceable configuration.
- The adversarial gate fails closed when a judge disappears and completes when staffing is valid.
- Durable continuity resides in the corpus, database, mailbox, and receipts—not in a vendor's private conversation memory.

**Not yet proved:**

- unattended wake-up of a dormant consumer chat conversation (the operator still supplies the turn);
- general portability to every model or chat product;
- complete cryptographic seat identity;
- that the session database accurately identifies the external occupant.

The last point is a real provenance defect. Both September 3 session rows retain `model_a_string = claude.ai-chat:claude-opus-4.8`, even though ChatGPT occupied the Researcher seat. Functional platform agnosticism is proved; occupant attribution is not yet platform-agnostic. Track and fix this before using the run as formal experimental evidence.

## OPERATOR RULINGS AND CONSEQUENCE

The operator explicitly deprioritized punch-list execution for this moment: **"I'm not worried about completing punchlist items at the moments—I'm just glad that we were able to reproduce a working system on a platform other than Claude."** The close therefore records the milestone without manufacturing a new build arc.

The operator also recorded the human consequence: **"I feel like I can work again"** and **"You've restored my faith in AI."** This belongs in the record because the system's dormant period was not caused by an exhausted research program; it was caused by loss of a usable Control relationship. Platform succession restored the working loop without discarding the institution built under the prior model.

## STATE LEFT

- MAIN engine healthy and idle after the completed lap.
- Challenger configured as `cerebras:gemma-4-31b`.
- Session `2026-09-03_14-13-03`: `incomplete_model_dead`, 3 cycles, preserved as the failed-closed lap.
- Session `2026-09-03_14-35-29`: `complete`, 2 cycles, successful cross-platform lap.
- Courier allowlist remains 19 operations.
- No application code deployed in this arc.
- Existing roadmap work deliberately not resumed.
- Secrets omitted from this record.

## NEXT

Run further ordinary work through the inherited Control seat when the operator chooses. Before presenting these sessions as formal platform-agnostic evidence, correct external-occupant provenance so the session row records the actual harness/model identity rather than the historical Claude placeholder.

**CROSS-REF:** sessions `2026-09-03_14-13-03` and `2026-09-03_14-35-29`; `live/agent_queue.md` September 3 fold; `live/PUNCH_LIST.md` September 3 DONE/OPEN entries; `live/OPERATING_MANUAL.md` role-provider and mailbox-seat currency; `live/CONTROL_HANDOFF.md` September 3 succession touchpoint; atomic close commit containing this record.
