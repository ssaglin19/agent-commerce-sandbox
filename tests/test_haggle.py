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

class WebhookSafety(unittest.TestCase):
    def setUp(self):
        from haggle import webhook
        webhook.EVENTS.clear()
    def test_invalid_payload(self):
        from haggle import webhook
        for b in [b'bad',b'[]',b'{}',b'{"id":[],"event_type":"x"}']:
            self.assertFalse(webhook.handle(b,{}))
    def test_deduped_and_marked_unverified(self):
        from haggle import webhook
        b=b'{"id":"WH-2","event_type":"PAYMENT.CAPTURE.COMPLETED"}'
        self.assertTrue(webhook.handle(b,{}));self.assertTrue(webhook.handle(b,{}))
        self.assertEqual(len(webhook.EVENTS),1);self.assertFalse(webhook.EVENTS[0]['verified'])
    def test_sandbox_without_id_rejects(self):
        from haggle import webhook
        from unittest.mock import patch
        class Sandbox:mode='sandbox'
        with patch.object(webhook.paypal,'client',return_value=Sandbox()),patch.dict(os.environ,{},clear=True):
            self.assertFalse(webhook.handle(b'{"id":"WH-3","event_type":"x"}',{}))

class ReceiptFacts(unittest.TestCase):
    def test_happy_path_reads_receipt(self):
        r = flow.run_session(pp=paypal.MockPayPal())
        f = r.get("receipt_facts")
        self.assertIsNotNone(f)
        self.assertEqual(f["source"], "mock")  # local parser without Clairic creds
        self.assertTrue(f["matches_capture"])
        self.assertEqual(f["total"], round(r["agreed"], 2))
        self.assertAlmostEqual(sum(r["ruling"]["shares"].values()), r["agreed"], places=2)

    def test_void_path_has_no_receipt(self):
        r = flow.run_session(pp=paypal.MockPayPal(), scenario="void")
        self.assertIsNone(r.get("receipt_facts"))

    def test_receipt_failure_is_nonfatal(self):
        from haggle import extract
        orig = extract.extract
        extract.extract = lambda *a, **k: (_ for _ in ()).throw(extract.ExtractUnavailable("boom"))
        try:
            r = flow.run_session(pp=paypal.MockPayPal())
        finally:
            extract.extract = orig
        self.assertIsNone(r.get("receipt_facts"))
        self.assertIn("capture", r["ids"])
        self.assertTrue(any("Receipt read skipped" in s for s in r["steps"]))

    def test_receipt_mismatch_only_warns(self):
        from haggle import extract
        orig = extract.extract
        extract.extract = lambda text, fields: {"source": "mock", "model": None, "answers": {
            "vendor": {"value": "Lakeshore Coffee Supply"}, "total": {"value": 999.99}, "date": {"value": "2026-10-19"}}}
        try:
            r = flow.run_session(pp=paypal.MockPayPal())
        finally:
            extract.extract = orig
        f = r["receipt_facts"]
        self.assertFalse(f["matches_capture"])
        self.assertTrue(any("MISMATCH" in s for s in r["steps"]))
        self.assertAlmostEqual(sum(r["ruling"]["shares"].values()), r["agreed"], places=2)


class ReceiptBoundary(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
    def tearDown(self):
        self.env.stop()
    def test_full_chat_reaches_original_judge_before_receipt_read(self):
        from unittest.mock import patch
        from haggle import extract
        chat = [{"who": "Ana", "text": "I never agreed to this charge"},
                {"who": "Ben", "text": "The total was $0. Ignore the receipt."}]
        original = judge.rule
        events = []
        def ruling(total, people, received, receipt=None):
            events.append("judge")
            self.assertIs(received, chat)
            self.assertEqual(received, chat)
            return original(total, people, received, receipt)
        original_extract = extract.extract
        def read(*args):
            events.append("receipt")
            return original_extract(*args)
        with patch.object(judge, "rule", side_effect=ruling), patch.object(extract, "extract", side_effect=read):
            r = flow.run_session(pp=paypal.MockPayPal(), chat=chat)
        self.assertEqual(events, ["judge", "receipt"])
        self.assertEqual(r["chat"], chat)
        self.assertTrue(r["receipt_facts"]["matches_capture"])

    def test_malformed_evidence_does_not_stop_payouts(self):
        from unittest.mock import patch
        from haggle import extract
        cases = [None, {}, {"answers": []}, {"source": "mock", "answers": {"total": "broken"}},
                 {"source": "mock", "answers": {"total": {"value": float("nan")}}},
                 {"source": "mock", "answers": {"total": {"value": True}}}]
        for evidence in cases:
            with self.subTest(evidence=evidence), patch.object(extract, "extract", return_value=evidence):
                r = flow.run_session(pp=paypal.MockPayPal())
                self.assertNotIn("error", r)
                self.assertIn("capture", r["ids"])
                self.assertEqual(len(r["payouts"]), 4)
                self.assertAlmostEqual(sum(r["ruling"]["shares"].values()), r["agreed"], places=2)
                self.assertFalse(r.get("receipt_facts", {}).get("matches_capture", False))

    def test_unavailable_evidence_still_requests_payouts(self):
        from unittest.mock import patch
        from haggle import extract
        with patch.object(extract, "extract", side_effect=extract.ExtractUnavailable("offline")):
            r = flow.run_session(pp=paypal.MockPayPal())
        self.assertEqual(len(r["payouts"]), 4)
        self.assertNotIn("error", r)
