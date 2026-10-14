import json, os, sys, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.pop("ANTHROPIC_API_KEY", None)
from haggle import paypal, wallet, webhook

CALLS = []
class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = self.rfile.read(n)
        CALLS.append((self.path, json.loads(body or b"{}") if body.startswith(b"{") else body))
        p = self.path
        if p == "/v1/oauth2/token": r = {"access_token": "tok"}
        elif p == "/v2/checkout/orders":
            r = {"id": "ORD1", "links": [{"rel": "self", "href": "x"}, {"rel": "payer-action", "href": "https://sandbox.paypal.test/approve?token=ORD1"}]}
        elif p.endswith("/authorize"): r = {"purchase_units": [{"payments": {"authorizations": [{"id": "AUTH1"}]}}]}
        elif p.endswith("/capture"): r = {"id": "CAP1"}
        elif p.endswith("/void"): r = {}
        elif p == "/v1/payments/payouts": r = {"batch_header": {"payout_batch_id": "B1"}}
        elif p == "/v1/notifications/verify-webhook-signature":
            r = {"verification_status": "SUCCESS" if CALLS[-1][1].get("webhook_id") == "WH" else "FAILURE"}
        else: self.send_response(404); self.end_headers(); return
        out = json.dumps(r).encode(); self.send_response(200); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

class WalletMock(unittest.TestCase):
    def test_start_finish_once(self):
        pp = paypal.MockPayPal()
        s = wallet.start("http://localhost:8000", "happy", pp=pp)
        self.assertIn("token=" + s["order"], s["approve_url"])
        r = wallet.finish(s["order"], pp=pp)
        self.assertEqual(r["path"], "wallet"); self.assertIn("capture", r["ids"])
        self.assertAlmostEqual(sum(r["ruling"]["shares"].values()), r["agreed"], places=2)
        self.assertIn("error", wallet.finish(s["order"], pp=pp))  # token is single use
    def test_default_client_keeps_state_between_start_and_finish(self):
        s = wallet.start("http://localhost:8000", "happy")
        r = wallet.finish(s["order"])
        self.assertNotIn("error", r); self.assertIn("capture", r["ids"])
    def test_unknown_token_refused(self):
        self.assertIn("error", wallet.finish("NOPE", pp=paypal.MockPayPal()))
    def test_void_path_captures_nothing(self):
        pp = paypal.MockPayPal(); s = wallet.start("http://localhost:8000", "void", pp=pp)
        r = wallet.finish(s["order"], pp=pp)
        self.assertEqual(r["ruling"]["decision"], "void"); self.assertNotIn("capture", r["ids"])

class WalletSandboxFake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Fake); threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.old = paypal.BASE; paypal.BASE = f"http://127.0.0.1:{cls.srv.server_port}"
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown(); paypal.BASE = cls.old
    def test_approval_order_sends_return_urls_and_reads_link(self):
        CALLS.clear(); pp = paypal.SandboxPayPal("id", "sec")
        oid, url = pp.create_approval_order(168.0, "Espresso", "http://h/wallet/return", "http://h/wallet/cancel")
        self.assertEqual(oid, "ORD1"); self.assertTrue(url.startswith("https://sandbox.paypal.test/approve"))
        body = [b for p, b in CALLS if p == "/v2/checkout/orders"][0]
        ec = body["payment_source"]["paypal"]["experience_context"]
        self.assertEqual(body["intent"], "AUTHORIZE"); self.assertEqual(ec["return_url"], "http://h/wallet/return")
        self.assertEqual(body["purchase_units"][0]["amount"]["value"], "168.00")
    def test_full_wallet_flow_against_fake(self):
        pp = paypal.SandboxPayPal("id", "sec")
        s = wallet.start("http://localhost:8000", "happy", pp=pp)
        r = wallet.finish(s["order"], pp=pp)
        self.assertEqual(r["ids"]["authorization"], "AUTH1"); self.assertEqual(r["ids"]["capture"], "CAP1")
    def test_webhook_verification_calls_paypal(self):
        os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_CLIENT_SECRET"] = "id", "sec"
        h = {"PAYPAL-AUTH-ALGO": "a", "PAYPAL-CERT-URL": "c", "PAYPAL-TRANSMISSION-ID": "t", "PAYPAL-TRANSMISSION-SIG": "s", "PAYPAL-TRANSMISSION-TIME": "x"}
        ev = {"id": "WH-9", "event_type": "PAYMENT.AUTHORIZATION.CREATED"}
        try:
            os.environ["PAYPAL_WEBHOOK_ID"] = "WH"; self.assertTrue(webhook.verify(ev, h))
            os.environ["PAYPAL_WEBHOOK_ID"] = "OTHER"; self.assertFalse(webhook.verify(ev, h))
            os.environ.pop("PAYPAL_WEBHOOK_ID"); self.assertFalse(webhook.verify(ev, h))
            self.assertFalse(webhook.verify(ev, {}))
        finally:
            for k in ("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_WEBHOOK_ID"): os.environ.pop(k, None)

if __name__ == "__main__": unittest.main()
