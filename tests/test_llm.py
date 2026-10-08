import os, sys, json, threading, subprocess, tempfile, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from haggle import llm, judge

class H(BaseHTTPRequestHandler):
    seen = []
    def do_POST(self):
        n = int(self.headers.get("content-length", 0)); body = self.rfile.read(n)
        H.seen.append((self.path, self.headers.get("Authorization"), body))
        if self.path == "/token": out = {"access_token": "FAKE", "expires_in": 3600}
        else: out = {"candidates": [{"content": {"parts": [{"text": H.reply}]}}]}
        b = json.dumps(out).encode(); self.send_response(200); self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
H.reply = "hi"

class T(unittest.TestCase):
    def setUp(self):
        for k in ("ANTHROPIC_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "GOOGLE_SA_JSON", "HAGGLE_MAX_LLM_CALLS_PER_DAY", "HAGGLE_VERTEX_URL", "HAGGLE_TOKEN_URL"): os.environ.pop(k, None)
        llm._calls = 0; llm._day.update(d=None, n=0); llm._tok.update(v=None, exp=0); H.seen.clear()
    def test_keyless_is_scripted(self):
        self.assertIsNone(llm.complete("s", "p")); self.assertEqual(llm.provider(), "scripted")
    def _vertex(self):
        srv = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
        d = tempfile.mkdtemp(); pem = os.path.join(d, "k.pem")
        subprocess.run(["openssl", "genrsa", "-out", pem, "2048"], check=True, capture_output=True)
        sa = os.path.join(d, "sa.json"); json.dump({"client_email": "x@y.iam", "project_id": "proj-from-key", "private_key": open(pem).read()}, open(sa, "w"))
        base = "http://127.0.0.1:%d" % srv.server_port
        os.environ.update(GOOGLE_SA_JSON=open(sa).read(), HAGGLE_VERTEX_URL=base + "/gen", HAGGLE_TOKEN_URL=base + "/token")
        return srv
    def test_vertex_path_and_cap(self):
        srv = self._vertex(); H.reply = "Ha."; os.environ["HAGGLE_MAX_LLM_CALLS"] = "2"
        self.assertEqual(llm.provider(), "vertex")
        self.assertEqual(llm.complete("s", "p"), "Ha."); llm.complete("s", "p")
        self.assertIsNone(llm.complete("s", "p"))  # cap
        self.assertEqual(sum(1 for s in H.seen if s[0] == "/gen"), 2)
        self.assertEqual([s[1] for s in H.seen if s[0] == "/gen"][0], "Bearer FAKE")
        os.environ.pop("HAGGLE_MAX_LLM_CALLS"); srv.shutdown()
    def test_day_cap_and_project_from_key(self):
        srv = self._vertex(); H.reply = "ok"; os.environ["HAGGLE_MAX_LLM_CALLS_PER_DAY"] = "1"
        self.assertEqual(llm.complete("s", "p"), "ok"); self.assertIsNone(llm.complete("s", "p"))
        self.assertEqual(llm.STATS["ok"] >= 1, True); srv.shutdown()
    def test_price_always_from_code(self):
        from haggle import negotiation
        srv = self._vertex(); H.reply = "Take $1.00 you cheapskate, 5 dollars!\nsecond line"
        d = negotiation.Deal("espresso", 200.0, 165.0, 168.0)
        t = negotiation._say("buyer", "Statler", "fb", 150.44, d)
        self.assertEqual(t, "Take  you cheapskate,  dollars! $150.44."); srv.shutdown()
    def test_judge_ai_weights_still_sum_exactly(self):
        srv = self._vertex(); H.reply = json.dumps({"weights": {"Ana": 9, "Ben": 1, "Cam": 3, "Dee": -5}, "verdict": "Ana drinks it all."})
        r = judge.rule(168.0, ["Ana", "Ben", "Cam", "Dee"], [{"who": "Ana", "text": "every day"}])
        self.assertAlmostEqual(sum(r["shares"].values()), 168.0, places=2); self.assertTrue(all(v > 0 for v in r["shares"].values())); srv.shutdown()
    def test_judge_bad_json_falls_back(self):
        srv = self._vertex(); H.reply = "not json"
        r = judge.rule(168.0, ["Ana", "Ben"], [{"who": "Ana", "text": "every day"}]); self.assertIn("lighter", r["verdict"]); srv.shutdown()
unittest.main() if __name__ == "__main__" else None
