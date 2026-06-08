# Proposal — self-enforcing deploy sign-off gate (STRUCTURAL, high weight)

**Status: PROPOSED, not deployed. Changes startup + deploy mechanics — operator review + sign-off trailer required. All investigation read-only.**

## Why this exists
Deploys to the session engine now carry an `Operator-Signoff:` trailer, but it is pure provenance — nothing checks it. The engine has zero runtime awareness of which commit it runs or whether that commit was signed (no `RAILWAY_GIT_COMMIT_SHA` reference, no version, no sign-off check anywhere in app.py). So the discipline that gates my own deploys (the gate I jumped once on d33/d34) is currently honor-system. This makes it binding.

## Mechanism (proportionate, in-architecture, fail-loud)
Railway auto-deploys from the repo, so the app cannot pre-block its own deploy. The realistic enforcement is at startup + the session-start path: an engine deployed from a commit that changed `app.py` **without** an `Operator-Signoff` trailer refuses to run sessions. An unsigned engine cannot pretend to be certified.

`verify_deploy_signoff()` at startup:
1. Read `RAILWAY_GIT_COMMIT_SHA` (the running commit) and the GitHub token (already available at runtime).
2. Fetch `/repos/{repo}/commits/{sha}` — message + changed files.
3. If the commit changed `app.py` and the message lacks `Operator-Signoff:` → `SIGNOFF_STATUS="unsigned"`, `PRODUCTION_LOCKED=True`.
4. **Fails SAFE**: missing SHA, API error, or a non-app.py commit leaves the instance UNLOCKED. The gate only locks on a deploy it can positively prove is an unsigned engine change — it never bricks the engine on a transient failure.

`signoff_blocked()` guards both session-start entry points (`agent_start` at the external mailbox path, `handle_start_session` at the operator dashboard): if `PRODUCTION_LOCKED` and `SIGNOFF_OVERRIDE != "1"`, refuse with a clear message and HTTP 403. The override env is the explicit dev/emergency escape hatch.

The verify function, globals, `signoff_blocked()` helper, and the `agent_start` guard are drafted and syntax-checked. Remaining mechanical wiring (described, not yet in the compiled draft): call `verify_deploy_signoff()` once at module init; add the same guard to `handle_start_session`; surface `SIGNOFF_STATUS` + commit SHA in `/diag/engine`.

```python
# guard, applied at the top of each start path:
_block = signoff_blocked()
if _block:
    return jsonify({"ok": False, "error": _block, "signoff_status": SIGNOFF_STATUS}), 403
```

## Honest limitations
- This is app-layer enforcement (an unsigned engine refuses to run sessions), not a pre-merge gate. The truly preventive mechanism is GitHub branch protection / a required status check that rejects an app.py change lacking the trailer — but that is repo config (operator hands) and would also block legitimate non-engine pushes unless scoped to app.py via a CI check. The app-layer gate is the proportionate in-architecture step; branch protection is the stronger complement if wanted.
- Depends on `RAILWAY_GIT_COMMIT_SHA` being present (verify on the instance — Railway sets it for git deploys). If absent, the gate is inert (fails safe to unlocked) until the var is available.
- Both MAIN and FARM would enforce independently; `SIGNOFF_OVERRIDE=1` is per-instance for dev/emergency.

## Verification plan
- Post-deploy (operator): the gate's own deploy must itself carry an `Operator-Signoff` trailer, else it locks itself on first boot — the gate proving itself. Confirm `/diag/engine` reports `signoff_status=signed` after a signed deploy, and `unsigned` + a refused start after an unsigned test deploy (or with `SIGNOFF_OVERRIDE` unset on a deliberately-unsigned commit).
- A controlled farm verification session confirms a signed build still starts normally.

## Operator action required
1. Decide app-layer gate alone vs. also adding GitHub branch protection.
2. Confirm `RAILWAY_GIT_COMMIT_SHA` is exposed on both instances (or supply the correct Railway commit env var name).
3. Deploy app.py with the `Operator-Signoff` trailer — and note the gate locks itself if that first deploy is unsigned, so the very first signed deploy is the bootstrap.

No deploy performed. No farm session run.
