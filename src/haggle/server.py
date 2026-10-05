"""Tiny stdlib web server: GET / page, POST /api/run -> session JSON. python -m haggle.server"""
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import flow

WEB = os.path.join(os.path.dirname(__file__), "web")

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, open(os.path.join(WEB, "index.html"), "rb").read(), "text/html")
        elif self.path == "/pool":
            from pool import server as ps
            self._send(200, open(os.path.join(ps.WEB, "index.html"), "rb").read(), "text/html")
        else: self._send(404, b"not found", "text/plain")
    def _limited(self):
        from . import ratelimit
        ip = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
        if ratelimit.allow(ip): return False
        self._send(429, json.dumps({"error": "Too many runs, wait a minute and try again."}).encode(), "application/json"); return True
    def do_POST(self):
        if self.path.startswith(("/api/pool", "/api/run")) and self._limited(): return
        if self.path.startswith("/api/pool"):
            from pool import session
            try: out = session.run("failure" if "scenario=failure" in self.path else "happy", haggle="haggle=1" in self.path)
            except Exception as e: out = {"error": str(e)}
            return self._send(200, json.dumps(out).encode(), "application/json")
        if self.path.startswith("/api/run"):
            self._send(200, json.dumps(flow.run_session(scenario=("void" if "scenario=void" in self.path else "happy"))).encode(), "application/json")
        elif self.path == "/webhook":
            n = int(self.headers.get("Content-Length", 0)); body = self.rfile.read(n)
            from . import webhook
            ok = webhook.handle(body, self.headers)
            self._send(200 if ok else 400, b"ok" if ok else b"bad", "text/plain")
        else: self._send(404, b"not found", "text/plain")

def main():
    port = int(os.environ.get("PORT", "8000"))
    print(f"Haggle Court on http://localhost:{port}"); ThreadingHTTPServer(("", port), H).serve_forever()

if __name__ == "__main__": main()
