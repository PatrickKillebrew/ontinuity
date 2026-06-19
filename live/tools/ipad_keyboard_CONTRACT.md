# iPad Keyboard — BUILD CONTRACT
# This file is the gate. Before declaring ANY version "done" or handing back to
# the operator, the contract MUST be re-read and every line re-verified against
# the actual deployed file. "Assumed" is not "verified." No line is checked off
# without evidence (JS parse, deployed-hash match, or operator-confirmed test).

## HARD REQUIREMENTS (must all hold simultaneously)

R1  LETTERS TRANSMIT
    Typing on the iPad soft keyboard lands characters on the laptop.
    Verify: operator types, chars appear on laptop. STATUS: PASS (v15+)

R2  CAPTURE FUNCTIONS DEFINED
    All JS helpers (activeMods, consumeOneShots, refreshModUI, setOK, setErr,
    syncEcho) are DEFINED, not just called. No ReferenceError on any handler.
    Verify: node --check passes AND grep confirms each `function X` exists.
    STATUS: PASS (v15+) — this was the root bug; never let it regress.

R3  SEND BUTTON = REAL ENTER
    Green SEND button is the ONLY thing that fires Enter on the laptop.
    Verify: operator taps SEND, laptop receives Enter. STATUS: PASS (v16+)

R4  RETURN KEY = PAGE BREAK ONLY (INERT)
    iPad Return inserts a local newline in the box, transmits NOTHING.
    Verify: operator hits Return, laptop receives nothing, no newline sent.
    STATUS: must confirm in v17 (was broken in v16).

R5  TRACKPAD ANCHORED + FULL HEIGHT
    Trackpad pinned right, fixed width (38%), spans full vertical height,
    does NOT move/reflow as typed text grows.
    Verify: operator types a lot; trackpad stays put and stays tall.
    STATUS: must confirm in v17 (height regressed in v16, fixed in v17).

R6  TRACKPAD SMOOTH (NO PERIODIC LAG)
    No ~1.5-2s skip/stutter. (Caused by per-keystroke disk log; removed v17.)
    Verify: operator moves trackpad continuously; no rhythmic hitch.
    STATUS: must confirm in v17.

R7  NO VISIBLE TEXT CLUTTER / INVISIBLE CAPTURE
    No "captured N" readout. The capture box text is invisible (color == bg),
    caret invisible. A normal user sees no weird text to fixate on or edit.
    Verify: operator looks at iPad; sees clean panel, no echo text, blank box.
    STATUS: must confirm in v17.

R8  NO SURPRISE CAPITALIZATION / AUTOCORRECT
    autocapitalize=none, autocorrect=off. Mid-sentence letters are not
    auto-capitalized after a box reset.
    Verify: operator types mid-sentence after reset; no unexpected capitals.
    STATUS: must confirm in v17.

R9  BOX RARELY RESETS
    Capture box large; reset threshold high (5000 chars) so it does not clear
    during normal use.
    Verify: extended typing doesn't trigger a visible reset. STATUS: confirm v17.

R10 TERMINAL TYPING WORKS (admin)
    Launched as admin, typing reaches a focused terminal window.
    Verify: operator types into terminal. STATUS: PASS (operator confirmed).

## VERIFICATION GATES (run EVERY build before handing back)
G1  python -m py_compile passes on the deployed file.
G2  node --check passes on the extracted page JS.
G3  deployed-file MD5 == locally-built MD5 (no truncation/stale file).
G4  grep: zero references to deleted elements (e.g. `echo`) remain.
G5  banner version string matches the version actually built.

## REGRESSION LOG (what broke before — never repeat)
- v8-v14: capture helpers called but never defined -> silent ReferenceError,
  keys never transmitted. (R2)
- iOS Safari does NOT fire keydown for letters; MUST use input event. (R1)
- iOS Safari needs HTTP/1.1 + no-cache headers or WS hangs "connecting". 
- Blanking the capture field mid-stream stops iOS input events.
- Per-keystroke disk log write caused ~2s trackpad lag. (R6)
- Fixed-height row shrank trackpad. Anchor position != shrink height. (R5)
- Stale Safari cache served old JS; no-cache headers + fresh tab required.
- Laptop sleep kills the seat process; hands die. Restart seat on wake.
