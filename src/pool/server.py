"""Stdlib web server. GET / page, POST /api/run?scenario=happy|failure. Run: python3 -m pool.server"""
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import session
WEB = os.path.join(os.path.dirname(__file__), "web")

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path in ("/", "/index.html"): self._send(200, open(os.path.join(WEB, "index.html"), "rb").read(), "text/html")
        else: self._send(404, b"not found", "text/plain")
    def do_POST(self):
        if self.path.startswith("/api/pool"):
            try: out = session.run("failure" if "scenario=failure" in self.path else "happy", haggle="haggle=1" in self.path)
            except Exception as e: out = {"error": str(e)}
            self._send(200, json.dumps(out).encode(), "application/json")
        else: self._send(404, b"not found", "text/plain")

def main():
    port = int(os.environ.get("PORT", "8000")); print(f"Pool on http://localhost:{port}")
    ThreadingHTTPServer(("", port), H).serve_forever()
if __name__ == "__main__": main()
