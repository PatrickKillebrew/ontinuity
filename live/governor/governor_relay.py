#!/usr/bin/env python3
"""Governor local relay (throwaway plumbing; real version serves from the
workspace endpoint with auth). Runs on the operator's machine. Holds the diag
key in memory, proxies read-only diag calls server-side (no CORS, no browser
block), and serves governor.html same-origin. The diag key NEVER enters the
committed HTML — paste it once when prompted, it stays in this process only.

Run:  DIAG_KEY=... python3 governor_relay.py    (then open http://localhost:8770)
   or just: python3 governor_relay.py            (it will prompt for the key)
"""
import json, os, sys, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

MAIN = "https://web-production-7eaf8.up.railway.app"
FARM = "https://ontinuity-farm-production.up.railway.app"
PORT = 8770
DIAG = os.environ.get("DIAG_KEY") or input("Paste DIAG_KEY (stays in this process only): ").strip()

def diag_get(base, path, params):
    params = dict(params); params["diag_key"] = DIAG
    url = f"{base}{path}?{urllib.parse.urlencode(params)}"
    try:
        return urllib.request.urlopen(url, timeout=30).read()
    except Exception as e:
        return json.dumps({"error": str(e)}).encode()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, body, ctype="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        qs = dict(urllib.parse.parse_qsl(u.query))
        if u.path == "/" or u.path == "/governor.html":
            try:
                self._send(open(os.path.join(os.path.dirname(__file__), "governor.html"), "rb").read(), "text/html")
            except Exception as e:
                self._send(f"<pre>governor.html not found beside relay: {e}</pre>", "text/html")
        elif u.path == "/api/engine":
            base = FARM if qs.get("instance") == "farm" else MAIN
            self._send(diag_get(base, "/diag/engine", {}))
        elif u.path == "/api/query":
            self._send(diag_get(MAIN, "/diag/api/query", {"sql": qs.get("sql", "")}))
        elif u.path == "/api/health":
            base = FARM if qs.get("instance") == "farm" else MAIN
            self._send(diag_get(base, "/diag/api/health", {}))
        else:
            self.send_response(404); self.end_headers()

if __name__ == "__main__":
    print(f"Governor relay on http://localhost:{PORT}  (Ctrl-C to stop)")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
