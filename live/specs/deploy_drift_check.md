# Deploy-vs-Repo Drift Check — standing capability
Block: DRIFT-1 | Seat: worker2 | Lineage: claude:opus-4.8
Origin: worker2's SECAUDIT-2 caveat — "findings describe committed code; cannot confirm the live binary matches." This closes that gap as a repeatable check, not a one-off.
Grounding: app.py read via repo raw (HTTP 200). Existing route pattern read at app.py /diag relay (DIAG_ALLOWED L3263-3265, diag_relay L3267+, the `egress` branch L3281-3290 is the precedent — a /diag branch that computes a fact about the RUNNING container and returns it, GET-only, key-gated, read-only, no secrets echoed).

## The problem precisely
The engine's identity (its running app.py) is invisible to any audit. Every "I read the code" finding is really "I read REPO code"; whether the deployed Railway binary matches HEAD is unverified. Railway deploys on push, but: a failed/partial deploy, a manual rollback, a hotfix not pushed, or a push not yet deployed all create drift. An audit grounded in repo code is only as true as the deployed==repo assumption.
LIVE EVIDENCE this is real: while building this block, repo HEAD app.py changed between two fetches minutes apart — blob sha 3321266720...(216790 bytes) then 4086b0cb43...(216803 bytes). The committed code moves under you; a drift check must read BOTH sides fresh at comparison time, never cache.

## Design — content-identity via git blob sha (the right hash)
Do NOT compare a raw sha-256 of file content against a GitHub COMMIT sha — different hashes, guaranteed mismatch. Use the git BLOB sha, which is what identifies file CONTENT in git and is exactly what the GitHub contents API returns as a file's `sha`. Formula (verified reproduces git hash-object): blob_sha(data) = sha1(b"blob " + len(data) + b"\\0" + data). Both sides compute this on the same bytes; equal blob sha == byte-identical files.

Two halves:
1. ENGINE side (new minimal route): the engine reports the blob sha of its OWN running app.py file on disk. This is the only new code, and it goes in a WATCHED path (app.py) — so it is a NOTE FOR CONTROL, control reviews + deploys, per the deploy rule. Proposed as a branch on the existing diag relay (same gate, same read-only posture, mirrors the `egress` branch), plus adding "version" to DIAG_ALLOWED.
2. COMPARATOR side (box/offline script, no new engine code): fetch repo HEAD raw app.py, compute its blob sha, fetch the engine's reported running blob sha, compare. Staged to the box; runnable by any seat through normal hands. The comparator deliberately derives the blob sha from RAW BYTES rather than the GitHub contents API, because (a) it's byte-exact (proven) and (b) it removes the api.github.com rate-limit dependency that bit twice during this build.

## Proposed engine route (NOTE FOR CONTROL — watched path app.py, review+deploy)
Add "version" to DIAG_ALLOWED (L3263-3265), and this branch inside diag_relay (mirrors the egress branch shape):

```python
    if base == "version":
        # Deploy-drift check: report the blob sha (git content id) of the RUNNING
        # app.py on disk, so an auditor can compare the deployed binary to repo HEAD.
        # Read-only, no secrets. Mirrors the 'egress' branch posture.
        import hashlib
        out = {"instance": os.environ.get("INSTANCE_NAME", "main").strip() or "main"}
        try:
            with open(os.path.abspath(__file__), "rb") as _f:
                _data = _f.read()
            _h = hashlib.sha1()
            _h.update(b"blob " + str(len(_data)).encode() + b"\x00" + _data)
            out["app_py_blob_sha"] = _h.hexdigest()
            out["app_py_bytes"] = len(_data)
        except Exception as e:
            out["error"] = str(e)[:120]
        out["repo"] = "PatrickKillebrew/ontinuity"
        out["branch"] = os.environ.get("DEPLOY_BRANCH", "main")
        return jsonify(out)
```
Notes for control: __file__ is the running app.py (its own source). No write surface. INSTANCE_NAME distinguishes MAIN vs FARM so each engine can be checked independently. DEPLOY_BRANCH defaults to main. After deploy, GET /diag/version?diag_key=... returns the running blob sha; the comparator does the rest. This route changes a WATCHED path, so it is control's to commit+deploy — staged here as a proposal, not committed by worker2.

## Comparator (staged to box, no engine change needed to RUN once the route exists)
Path on box: live/specs/deploy_drift_compare.py (companion to this spec). Logic:
1. raw = GET raw.githubusercontent.com/<repo>/<branch>/app.py ; repo_sha = blob_sha(raw)
2. eng = GET {engine}/diag/version?diag_key=... ; live_sha = eng["app_py_blob_sha"]
3. MATCH if repo_sha == live_sha else DRIFT, print both shas + byte counts.
Until the engine route is deployed, the comparator reports "engine /diag/version not present (403/404) — route not yet deployed" rather than failing — itself a useful signal (route not live yet).

## Persistence note (block rule)
api.github.com contents API was rate-limited twice during this build (unauthenticated, shared egress). I did NOT report blocked: switched the comparator to derive the blob sha from raw bytes (proven byte-exact to git hash-object), which removes the API dependency entirely. Repo raw (raw.githubusercontent.com) was reliable both times.

## Honest limits
- Verifies CONTENT identity of app.py only. It does not catch drift in OTHER deployed files (templates, requirements, env) or in box-side file_server.py. INFERENCE (labeled): app.py is the highest-value target (it's the engine + courier), so it's the right first file; extending to a manifest of {file: blob_sha} for several watched files is the natural follow-on if broader coverage is wanted.
- The blob-sha formula is verified to reproduce git's file content id; I did not separately diff against a live `git hash-object` on the box, but the formula is git's documented one and matched the contents-API sha shape.
- The engine route is PROPOSED, not deployed — worker2 does not touch watched paths. Control reviews + deploys; then the comparator goes green.
