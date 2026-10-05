import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.pop("ANTHROPIC_API_KEY", None)
from haggle import flow, judge, negotiation, paypal

class T(unittest.TestCase):
    def test_deal_in_range(self):
        d = negotiation.run(); self.assertIsNotNone(d.agreed); self.assertTrue(165 <= d.agreed <= 200)
    def test_shares_sum(self):
        r = judge.rule(168.0, ["a", "b", "c"], [{"who": "a", "text": "skip it"}])
        self.assertAlmostEqual(sum(r["shares"].values()), 168.0, places=2)
    def test_flow_mock(self):
        r = flow.run_session(pp=paypal.MockPayPal())
        self.assertEqual(r["mode"], "mock"); self.assertEqual(len(r["payouts"]), 4)
        self.assertAlmostEqual(sum(r["ruling"]["shares"].values()), r["agreed"], places=2)


class W(unittest.TestCase):
    def test_webhook_dev_mode(self):
        from haggle import webhook
        self.assertTrue(webhook.handle(b'{"event_type":"PAYMENT.AUTHORIZATION.CREATED","id":"WH-1"}', {}))
        self.assertEqual(webhook.EVENTS[-1]["type"], "PAYMENT.AUTHORIZATION.CREATED")

class F(unittest.TestCase):
    def test_void_scenario(self):
        r = flow.run_session(pp=paypal.MockPayPal(), scenario="void")
        self.assertEqual(r["ruling"]["decision"], "void"); self.assertEqual(r["payouts"], [])
        self.assertNotIn("capture", r["ids"])
    def test_happy_has_ids(self):
        r = flow.run_session(pp=paypal.MockPayPal())
        self.assertEqual(r["ruling"]["decision"], "capture"); self.assertIn("capture", r["ids"])
if __name__ == "__main__": unittest.main()
