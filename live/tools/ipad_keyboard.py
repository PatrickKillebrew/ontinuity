"""
iPad -> Windows keyboard + trackpad bridge  (v4)

THE MODEL (three separated jobs, zero overlap):
  * Apple's Return key  = line break INSIDE the iPad box only. Never transmitted.
  * Green DELIVER button = drops your composed text (paragraph breaks intact,
                           all INERT) into the focused laptop app. No Enter is
                           sent, so nothing submits. Tap again to add another
                           block. No manual copy/paste -- it uses the clipboard
                           invisibly + Ctrl+V.
  * Blue  SEND (Enter)  = the ONLY key in the whole system that transmits a real
                           Enter to the laptop, which the app reads as "submit".

Delivery is paste-based so embedded line breaks arrive as inert text (they just
move the cursor down a row) and can never trigger an early submit.

Also: Ctrl/Shift/Alt/Win modifiers, Esc, arrows, function keys, and a trackpad
(drag=move, tap=left click, 2-finger tap=right click, 2-finger drag=scroll).

Python 3 standard library only. Win32 SendInput via ctypes. LAN only.
"""

import ctypes
import ctypes.wintypes as w
import json
import socket
import time
import http.server
import socketserver
import hashlib
import base64
import struct
import threading

# ---------------------------------------------------------------------------
# Win32 plumbing
# ---------------------------------------------------------------------------
INPUT_KEYBOARD = 1
INPUT_MOUSE = 0
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800

ULONG_PTR = ctypes.wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", w.WORD), ("wScan", w.WORD), ("dwFlags", w.DWORD),
                ("time", w.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", w.LONG), ("dy", w.LONG), ("mouseData", w.DWORD),
                ("dwFlags", w.DWORD), ("time", w.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", w.DWORD), ("wParamL", w.WORD), ("wParamH", w.WORD)]


class _INPUTunion(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", w.DWORD), ("u", _INPUTunion)]


SendInput = ctypes.windll.user32.SendInput
SendInput.argtypes = (w.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype = w.UINT


def _send(inp):
    return SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


VK = {
    "enter": 0x0D, "backspace": 0x08, "tab": 0x09, "escape": 0x1B,
    "space": 0x20, "delete": 0x2E, "insert": 0x2D,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "capslock": 0x14, "printscreen": 0x2C,
    "ctrl": 0xA2, "shift": 0xA0, "alt": 0xA4, "win": 0x5B,
    "c": 0x43, "v": 0x56,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}
EXT = {"left", "up", "right", "down", "home", "end", "pageup", "pagedown",
       "delete", "insert", "win", "printscreen"}


def _vk_down(vk, ext=False):
    _send(INPUT(type=INPUT_KEYBOARD,
                u=_INPUTunion(ki=KEYBDINPUT(vk, 0, KEYEVENTF_EXTENDEDKEY if ext else 0, 0, 0))))


def _vk_up(vk, ext=False):
    f = KEYEVENTF_KEYUP | (KEYEVENTF_EXTENDEDKEY if ext else 0)
    _send(INPUT(type=INPUT_KEYBOARD, u=_INPUTunion(ki=KEYBDINPUT(vk, 0, f, 0, 0))))


def type_char(ch):
    code = ord(ch)
    _send(INPUT(type=INPUT_KEYBOARD,
                u=_INPUTunion(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, 0))))
    _send(INPUT(type=INPUT_KEYBOARD,
                u=_INPUTunion(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0))))


def press_named(name):
    vk = VK.get(name)
    if vk is None:
        return
    ext = name in EXT
    _vk_down(vk, ext); _vk_up(vk, ext)


def press_chord(mods, key):
    held = []
    for m in mods:
        vk = VK.get(m)
        if vk is not None:
            _vk_down(vk, m in EXT); held.append((vk, m in EXT))
    try:
        if key in VK:
            press_named(key)
        elif key and len(key) == 1:
            ch = key.upper()
            vk = ord(ch) if ("A" <= ch <= "Z" or "0" <= ch <= "9") else None
            if vk is not None:
                _vk_down(vk); _vk_up(vk)
            else:
                type_char(key)
    finally:
        for vk, ext in reversed(held):
            _vk_up(vk, ext)


# ---- clipboard (deliver text without typing it) ----
def set_clipboard(text):
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    k = ctypes.windll.kernel32
    u = ctypes.windll.user32
    # Declare arg/return types so 64-bit pointers are not truncated.
    k.GlobalAlloc.argtypes = (w.UINT, ctypes.c_size_t)
    k.GlobalAlloc.restype = ctypes.c_void_p
    k.GlobalLock.argtypes = (ctypes.c_void_p,)
    k.GlobalLock.restype = ctypes.c_void_p
    k.GlobalUnlock.argtypes = (ctypes.c_void_p,)
    u.OpenClipboard.argtypes = (ctypes.c_void_p,)
    u.SetClipboardData.argtypes = (w.UINT, ctypes.c_void_p)
    u.SetClipboardData.restype = ctypes.c_void_p
    if not u.OpenClipboard(0):
        return False
    try:
        u.EmptyClipboard()
        data = text.encode("utf-16-le") + b"\x00\x00"
        h = k.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h:
            return False
        p = k.GlobalLock(h)
        if not p:
            return False
        ctypes.memmove(p, data, len(data))
        k.GlobalUnlock(h)
        if not u.SetClipboardData(CF_UNICODETEXT, h):
            return False
        return True
    finally:
        u.CloseClipboard()


def deliver_block(text):
    """Put text on clipboard (breaks intact, inert) and paste with Ctrl+V."""
    if not text:
        return
    if set_clipboard(text):
        time.sleep(0.03)
        press_chord(["ctrl"], "v")


# ---- mouse ----
def mouse_move(dx, dy):
    _send(INPUT(type=INPUT_MOUSE,
                u=_INPUTunion(mi=MOUSEINPUT(int(dx), int(dy), 0, MOUSEEVENTF_MOVE, 0, 0))))


def mouse_click(button="left"):
    d, u = (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP) if button == "right" \
        else (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP)
    _send(INPUT(type=INPUT_MOUSE, u=_INPUTunion(mi=MOUSEINPUT(0, 0, 0, d, 0, 0))))
    _send(INPUT(type=INPUT_MOUSE, u=_INPUTunion(mi=MOUSEINPUT(0, 0, 0, u, 0, 0))))


def mouse_scroll(amount):
    _send(INPUT(type=INPUT_MOUSE,
                u=_INPUTunion(mi=MOUSEINPUT(0, 0, int(amount), MOUSEEVENTF_WHEEL, 0, 0))))


def handle_event(ev):
    t = ev.get("t")
    if t == "char":
        type_char(ev.get("v", ""))
    elif t == "enter":
        press_named("enter")
    elif t == "key":
        press_named(ev.get("v", ""))
    elif t == "chord":
        press_chord(ev.get("mods", []), ev.get("key", ""))
    elif t == "move":
        mouse_move(ev.get("dx", 0), ev.get("dy", 0))
    elif t == "click":
        mouse_click(ev.get("b", "left"))
    elif t == "scroll":
        mouse_scroll(ev.get("a", 0))


# ---------------------------------------------------------------------------
# iPad page
# ---------------------------------------------------------------------------
PAGE = r"""<!doctype html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>iPad Keyboard</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing:border-box; -webkit-user-select:none; user-select:none;
      -webkit-tap-highlight-color:transparent; }
  html,body { margin:0; height:100%; background:#0f1115; color:#e6e8ec;
              font-family:-apple-system,system-ui,sans-serif; overflow:hidden; }
  #wrap { display:flex; flex-direction:column; height:100%; padding:8px; gap:7px; }
  #status { font-size:12px; color:#8b93a3; text-align:center; }
  #status.ok { color:#5fd08a; }
  .strip { display:flex; gap:5px; }
  .strip.fk { flex-wrap:wrap; }
  button { flex:1; padding:11px 3px; font-size:14px; border:none; border-radius:8px;
           background:#222732; color:#e6e8ec; min-width:0; }
  button:active { background:#2e3543; }
  button.fk { flex:0 0 auto; min-width:46px; font-size:12px; }
  button.mod { background:#2a3550; font-weight:600; }
  button.mod.armed { background:#3b82f6; color:#fff; }
  button.mod.locked { background:#9333ea; color:#fff; }
  button.deliver { background:#15803d; color:#fff; font-weight:700; }
  button.deliver:active { background:#1f9d4d; }
  button.enter { background:#2563eb; color:#fff; font-weight:700; }
  button.enter:active { background:#3b82f6; }
  .main { flex:1; display:flex; gap:7px; min-height:120px; }
  #pad { flex:1; font-size:18px; line-height:1.4; background:#171a21;
         color:#e6e8ec; border:1px solid #2a2f3a; border-radius:10px;
         padding:11px; resize:none; outline:none;
         -webkit-user-select:text; user-select:text; }
  #trackpad { flex:0 0 36%; background:#13161c; border:1px dashed #2a2f3a;
              border-radius:10px; display:flex; align-items:center;
              justify-content:center; color:#4b5563; font-size:12px;
              text-align:center; touch-action:none; line-height:1.6; }
  #trackpad.active { background:#1a1f29; border-color:#3b82f6; }
  .sec { font-size:9px; color:#4b5563; text-transform:uppercase;
         letter-spacing:.05em; margin:1px 0 -3px 2px; }
  .hint { font-size:10px; color:#6b7280; text-align:center; }
</style></head>
<body>
<div id="wrap">
  <div id="status">connecting...</div>

  <div class="sec">modifiers (tap = next key, double-tap = lock) &mdash; for Windows commands</div>
  <div class="strip">
    <button class="mod" data-mod="ctrl">Ctrl</button>
    <button class="mod" data-mod="shift">Shift</button>
    <button class="mod" data-mod="alt">Alt</button>
    <button class="mod" data-mod="win">Win</button>
    <button data-k="escape">Esc</button>
  </div>
  <div class="strip">
    <button data-k="home">Home</button>
    <button data-k="left">&#8592;</button>
    <button data-k="up">&#8593;</button>
    <button data-k="down">&#8595;</button>
    <button data-k="right">&#8594;</button>
    <button data-k="end">End</button>
    <button data-k="delete">Del</button>
  </div>

  <div class="sec">function keys</div>
  <div class="strip fk">
    <button class="fk" data-k="f1">F1</button><button class="fk" data-k="f2">F2</button>
    <button class="fk" data-k="f3">F3</button><button class="fk" data-k="f4">F4</button>
    <button class="fk" data-k="f5">F5</button><button class="fk" data-k="f6">F6</button>
    <button class="fk" data-k="f7">F7</button><button class="fk" data-k="f8">F8</button>
    <button class="fk" data-k="f9">F9</button><button class="fk" data-k="f10">F10</button>
    <button class="fk" data-k="f11">F11</button><button class="fk" data-k="f12">F12</button>
  </div>

  <div class="main">
    <div class="capwrap">
      <div id="echo" tabindex="-1">Tap the dark strip below, then type. Keys go to the laptop â€” watch the laptop, not here.</div>
      <textarea id="cap" autocapitalize="sentences" autocomplete="on"
                autocorrect="on" spellcheck="true" aria-label="key capture"></textarea>
    </div>
    <div id="trackpad">drag = move<br>tap = click<br>2 fingers tap = right<br>2 fingers drag = scroll</div>
  </div>

  <div class="hint">One cursor only â€” the laptopâ€™s. Type blind here and watch the laptop. The green strip just echoes your last keys.</div>
</div>

<script>
const status=document.getElementById('status');
const cap=document.getElementById('cap');
const echo=document.getElementById('echo');
let echoText='';
const trackpad=document.getElementById('trackpad');
let ws=null, wsReady=false, queue=[];
function connectWS(){
  try{
    var proto = location.protocol==='https:'?'wss':'ws';
    ws = new WebSocket(proto+'://'+location.host+'/ws');
    ws.onopen=function(){ wsReady=true; setOK();
      // drain anything buffered while connecting
      while(queue.length){ ws.send(JSON.stringify(queue.shift())); } };
    ws.onclose=function(){ wsReady=false; setErr('reconnecting...'); setTimeout(connectWS,600); };
    ws.onerror=function(){ try{ws.close();}catch(e){} };
  }catch(e){ setErr('cannot reach laptop'); setTimeout(connectWS,1000); }
}
function send(ev){
  if(wsReady){ try{ ws.send(JSON.stringify(ev)); return; }catch(e){ wsReady=false; } }
  queue.push(ev); if(queue.length>500) queue.shift();
}

// GREEN: deliver the composed block into the app (no Enter). Keeps text so you
// can review/add; clears after delivering so the next block starts fresh.
// BLUE: the one real Enter.


// LIVE keyboard (v9 capture): accumulate + diff, NEVER blank mid-stream.
// iOS keeps feeding keys because the field is a normal growing textarea; we
// send only the newly-changed characters. This is the capture that typed
// reliably on-device; v8 regressed by blanking on every key (iOS then stops
// firing input events). Enter/Tab/Backspace come through keydown below.
function pushEcho(s){ echoText=(echoText+s).slice(-80); echo.textContent=echoText||' '; }
var last='';
cap.addEventListener('input', function(){
  var now=cap.value;
  var m=activeMods();
  if(now.length>last.length && now.indexOf(last)===0){
    var added=now.slice(last.length);
    if(m.length && added.length===1){ send({t:'chord',mods:m,key:added}); consumeOneShots(); }
    else { for(var i=0;i<added.length;i++){ var ch=added[i]; if(ch==='\n') send({t:'key',v:'enter'}); else send({t:'char',v:ch}); } }
    pushEcho(added);
  } else if(now.length<last.length && last.indexOf(now)===0){
    var n=last.length-now.length;
    for(var j=0;j<n;j++){ send({t:'key',v:'backspace'}); echoText=echoText.slice(0,-1); }
    echo.textContent=echoText||' ';
  } else if(now!==last){
    // mid-edit / autocorrect replacement: backspace the divergent tail, retype it
    var k=0, L=Math.min(now.length,last.length);
    while(k<L && now[k]===last[k]) k++;
    for(var b=0;b<last.length-k;b++) send({t:'key',v:'backspace'});
    var tail=now.slice(k);
    for(var t=0;t<tail.length;t++){ var c2=tail[t]; if(c2==='\n') send({t:'key',v:'enter'}); else send({t:'char',v:c2}); }
    pushEcho(tail);
  }
  last=now;
  // only reset when it gets long, never mid-keystroke
  if(now.length>300){ cap.value=''; last=''; }
});
// Enter / Tab / Backspace via keydown (an empty field's input event misses these).
cap.addEventListener('keydown', function(e){
  var key=e.key; var m=activeMods();
  if(key==='Enter'){ if(m.length){send({t:'chord',mods:m,key:'enter'});consumeOneShots();}else send({t:'key',v:'enter'}); pushEcho('\u23ce'); e.preventDefault(); return; }
  if(key==='Tab'){ if(m.length){send({t:'chord',mods:m,key:'tab'});consumeOneShots();}else send({t:'key',v:'tab'}); e.preventDefault(); return; }
  // Backspace only handled here when field is already empty (otherwise input-diff catches it)
  if(key==='Backspace' && cap.value===''){ send({t:'key',v:'backspace'}); echoText=echoText.slice(0,-1); echo.textContent=echoText||' '; e.preventDefault(); return; }
});

// named keys with optional modifier chord
document.querySelectorAll('button[data-k]').forEach(b=>{
  b.addEventListener('click',e=>{e.preventDefault();
    const name=b.getAttribute('data-k'); const m=activeMods();
    if(m.length){send({t:'chord',mods:m,key:name});consumeOneShots();}
    else send({t:'key',v:name});
    cap.focus();});
});

// modifier buttons: tap=arm, double-tap=lock
document.querySelectorAll('button[data-mod]').forEach(b=>{
  const name=b.getAttribute('data-mod'); let tt=null;
  b.addEventListener('click',e=>{e.preventDefault();
    if(tt){clearTimeout(tt);tt=null;mods[name]=(mods[name]==='locked')?'off':'locked';refreshModUI();cap.focus();return;}
    tt=setTimeout(()=>{tt=null;mods[name]=(mods[name]==='off')?'armed':'off';refreshModUI();cap.focus();},230);});
});

// trackpad
let lastX=0,lastY=0,moved=false,startT=0,twoFinger=false,lastScrollY=0;
const TAP_MS=250,TAP_SLOP=8,SENS=1.6;
trackpad.addEventListener('touchstart',e=>{e.preventDefault();trackpad.classList.add('active');
  twoFinger=e.touches.length>=2;const t=e.touches[0];lastX=t.clientX;lastY=t.clientY;lastScrollY=t.clientY;
  moved=false;startT=Date.now();},{passive:false});
trackpad.addEventListener('touchmove',e=>{e.preventDefault();const t=e.touches[0];
  if(e.touches.length>=2){const dy=t.clientY-lastScrollY;lastScrollY=t.clientY;
    if(Math.abs(dy)>1){send({t:'scroll',a:Math.round(dy*4)});moved=true;}return;}
  const dx=t.clientX-lastX,dy=t.clientY-lastY;
  if(Math.abs(dx)>TAP_SLOP||Math.abs(dy)>TAP_SLOP)moved=true;
  if(dx||dy)send({t:'move',dx:dx*SENS,dy:dy*SENS});
  lastX=t.clientX;lastY=t.clientY;},{passive:false});
trackpad.addEventListener('touchend',e=>{e.preventDefault();trackpad.classList.remove('active');
  const quick=(Date.now()-startT)<TAP_MS;
  if(quick&&!moved)send({t:'click',b:twoFinger?'right':'left'});
  twoFinger=false;},{passive:false});

connectWS();
refreshModUI(); cap.focus();
</script>
</body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _ws_handshake(self):
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            return False
        accept = base64.b64encode(hashlib.sha1(
            (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        return True

    def _ws_recv(self):
        # read one frame, return decoded text payload (or None on close)
        rf = self.rfile
        hdr = rf.read(2)
        if len(hdr) < 2:
            return None
        b1, b2 = hdr[0], hdr[1]
        opcode = b1 & 0x0F
        masked = b2 & 0x80
        ln = b2 & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", rf.read(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", rf.read(8))[0]
        mask = rf.read(4) if masked else b"\x00\x00\x00\x00"
        data = rf.read(ln)
        if opcode == 0x8:   # close
            return None
        out = bytearray(len(data))
        for i in range(len(data)):
            out[i] = data[i] ^ mask[i % 4]
        return out.decode("utf-8", "ignore")

    def _ws_loop(self):
        # Each text frame is one JSON event (or a JSON array of events).
        while True:
            try:
                msg = self._ws_recv()
            except Exception:
                break
            if msg is None:
                break
            if not msg:
                continue
            try:
                payload = json.loads(msg)
            except Exception:
                continue
            evs = payload if isinstance(payload, list) else [payload]
            for ev in evs:
                try:
                    handle_event(ev)
                except Exception:
                    pass

    def do_GET(self):
        if self.path == "/ws" and self.headers.get("Upgrade", "").lower() == "websocket":
            if self._ws_handshake():
                self._ws_loop()
            return
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/key":
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"[]"
        try:
            for ev in json.loads(raw.decode("utf-8") or "[]"):
                handle_event(ev)
            self.send_response(200)
        except Exception:
            self.send_response(400)
        self.send_header("Content-Length", "0")
        self.end_headers()


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def main():
    port = 8765
    ip = lan_ip()
    print("=" * 56)
    print("  iPad keyboard (v9: WebSocket + stable capture) is running.")
    print("  On the iPad (same Wi-Fi), open Safari and go to:")
    print()
    print("      http://%s:%d" % (ip, port))
    print()
    print("  Type live. One cursor only. Ctrl+C here to stop.")
    print("  Ctrl+C here to stop.")
    print("=" * 56)
    with socketserver.ThreadingTCPServer(("0.0.0.0", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")


if __name__ == "__main__":
    main()
