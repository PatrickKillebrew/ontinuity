# iPad Keyboard — BUILD CORPUS
# The running record of this tool: what was tried, what broke, the fix, and
# verified-vs-assumed. Started AFTER the painful v1-v23 slog precisely because
# its absence caused repeated rediscovery of the same facts. This corpus is the
# memory the next build phase (dial-out/relay) starts from. Append, never erase.

## WHAT THE TOOL IS
A stdlib-only Python server runs on a Windows laptop. An iPad opens a web page
in Safari over the LAN and injects keystrokes + trackpad input into the laptop's
focused window via Win32 SendInput. No App Store, no purchase. The keyboard is
a keystroke STREAMER (a typewriter), not a synced document editor.

## CONFIRMED-GOOD BUILD
v23 — operator-verified on device 2026-06-18. Archived on the laptop as
keyboard_v23_CONFIRMED.py. Deployed file: keyboard.py + page.html in
C:\Users\kille\Documents\iPad Keyboard\.

## ARCHITECTURE (as of v23)
- Transport: hand-rolled WebSocket (RFC6455) over HTTP, stdlib only.
  HTTP POST /key fallback exists if WS won't open.
- Server: ThreadingTCPServer + BaseHTTPRequestHandler. protocol_version MUST be
  "HTTP/1.1" or iOS Safari hangs the WS handshake on "connecting...".
- Page served from page.html, RE-READ FRESH PER REQUEST (v18+). Server writes
  page.html from embedded PAGE on startup. => UI changes need only a page.html
  push + iPad reload, NO server restart. (Python-logic changes still need a restart.)
- Capture: a VISIBLE textarea #cap whose text color == background (#0e1117 on
  #0e1117), caret transparent => "invisible ink." Real text is there for iOS to
  autocorrect/capitalize; the human eye sees nothing. Box NEVER auto-resets
  (v22+), so iOS keeps autocorrect/caps context indefinitely.
- Letters captured via the INPUT event (diff against last value). NOT keydown.
- Special keys (Tab, Backspace) via keydown. Enter handled in keydown.
- Trackpad: separate touch surface, anchored right at fixed 38% width,
  align-self stretch to full height. Does not reflow as text grows.

## KEY BINDINGS (v23)
- Return key  -> sends Shift+Enter chord = paragraph break / newline that does
  NOT submit in chat apps. (Confirmed: on a physical USB keyboard the operator
  also uses Shift+Enter for newline-without-send in Claude; so Return mapping to
  Shift+Enter is correct and consistent.)
- SEND button (green, in panel) -> sends plain Enter = submit. The insurance key
  for apps where Enter submits.
- Modifier keys (Ctrl/Shift/Alt/Win): tap = arm for next key, double-tap = lock.

## THE BIG BUGS (root causes — never rediscover these)
1. MISSING JS HELPERS (the months-long killer). activeMods, consumeOneShots,
   refreshModUI, setOK, setErr, syncEcho were CALLED but never DEFINED across
   v8-v14 -> silent ReferenceError killed every keystroke handler. Trackpad
   survived because it called none of them. FIX: define all helpers (v15).
   GATE: node --check the page JS AND grep each `function X` exists.
2. iOS SAFARI does NOT fire keydown for letter keys on the soft keyboard. It
   fires keydown only for Enter/Tab/Backspace. Letters MUST be captured via the
   input event. (Proven by the kb_events.log: typing produced zero char/key
   events, only trackpad move events.)
3. iOS Safari WS handshake hangs on "connecting..." unless server speaks
   HTTP/1.1 (set protocol_version) and every response sets Content-Length.
4. STALE PAGE: the server cached PAGE in memory at launch; pushing a new file
   didn't change what the iPad got until restart. Also Safari cached the page
   hard. FIX: no-cache headers + serve page.html fresh per request (v18).
5. #pad / #cap ID MISMATCH: the CSS rule was named #pad but the element id was
   cap, so the capture box was UNSTYLED for many versions; every "make it
   invisible" edit targeted #cap and silently matched nothing. FIX: rename rule
   to #cap (v19). LESSON: verify the rule lands on the actual element id.
6. Blanking the capture field mid-stream stops iOS firing input events. Do not
   clear the box during typing.
7. Per-keystroke disk log write (a diagnostic) caused ~1.5-2s trackpad lag.
   Removed for production (v17).
8. autocapitalize/autocorrect: turning them OFF killed useful iOS typing. They
   work fine on the invisible-ink box AS LONG AS the box is never cleared.
   Keep autocapitalize="sentences", autocorrect="on" + never reset the box.

## HARNESS / OPS LESSONS (reverse-connection hands used to build this)
- Laptop hands = laptop_seat.py dials OUT to the engine mailbox, polls for task
  messages, executes scoped run/read/write, posts results back. No inbound port.
- mailbox reply_to is NOT persisted by the engine (comes back None). Correlate
  results by: drain control mailbox first, send task, take first kind=result
  from seat=laptop. (Crossed-signal bug made earlier reads grab stale results
  and looked like truncation/size limits — it was NOT a size limit; 22KB
  transfers round-trip fine.)
- Large file to a folder OUTSIDE the seat's scope (C:\donkeycar): write into
  scope, then `copy /Y` to the target via run op. Verify by MD5 hash match.
- curl through the hands is flaky for fetching the served page; use python
  urllib on the laptop instead.
- Laptop SLEEP kills the seat process -> hands die -> restart laptop_seat.py.
- Build .exe pieces (PyInstaller) were downloaded; .exe packaging is a planned
  step for non-technical users (bundle Python, request admin, show URL/QR).

## VERIFY-BEFORE-HANDOFF GATES (run every build)
G1 python -m py_compile passes on deployed file.
G2 node --check passes on extracted page JS.
G3 deployed-file MD5 == locally-built MD5 (no truncation / stale file).
G4 grep: zero references to deleted elements remain.
G5 served-page check via urllib confirms the NEW code is what's served.

## NEXT PHASE: DIAL-OUT / RELAY (portable keyboard, works anywhere incl. Starbucks)
PROBLEM: current keyboard needs iPad+laptop on the SAME private LAN. Public Wi-Fi
(Starbucks) uses client isolation that blocks device-to-device, so the direct
iPad->laptop:8765 connection cannot form.
SOLUTION (same pattern as laptop_seat hands): both iPad and laptop dial OUT to
the engine; the engine relays the keystroke/trackpad stream between them. Neither
device needs to reach the other directly => works on ANY internet connection.
STATUS: not started. The relay, outbound-dial, and auth are already proven from
the laptop_seat work, so this is an extension, not from-scratch.
OPEN QUESTIONS for the dial-out build:
- Latency: the relay adds a hop; keystroke streaming is latency-sensitive. Need
  to measure round-trip through the engine vs the direct LAN WS.
- The engine mailbox is request/response polling; a keystroke stream may need a
  persistent/low-latency channel, not 2s polling. May need a streaming endpoint.
- Pairing: how does a given iPad find its OWN laptop through the relay (a seat
  id / pairing code) so two users don't cross streams.
