import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from haggle import extract

RECEIPT = "Receipt from Lakeshore Roasters. Seller: Lakeshore Roasters. Total: $168.00. Date: 2026-10-19."

class ExtractMockTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("CLOUDFLARE_ACCOUNT_ID", None); os.environ.pop("CLOUDFLARE_API_TOKEN", None)

    def test_receipt_fields(self):
        out = extract.extract(RECEIPT, dict(extract.RECEIPT_FIELDS))
        a = out["answers"]
        self.assertEqual(out["source"], "mock")
        self.assertEqual(a["vendor"]["value"], "Lakeshore Roasters")
        self.assertEqual(a["total"]["value"], 168.00)
        self.assertEqual(a["date"]["value"], "2026-10-19")

    def test_missing_date_is_null(self):
        out = extract.extract("Seller: Lakeshore Roasters. Total: $168.00.", dict(extract.RECEIPT_FIELDS))
        self.assertIsNone(out["answers"]["date"]["value"])

    def test_claim_spans_are_verbatim(self):
        chat = "Ana: I'm out, not paying for this.\nBen: I'll use it every day."
        out = extract.extract(chat, dict(extract.CHAT_FIELDS))
        opt = out["answers"]["opt_outs"]["value"]
        heavy = out["answers"]["heavy_use_claims"]["value"]
        self.assertEqual(opt, ["Ana: I'm out, not paying for this"])
        self.assertEqual(heavy, ["Ben: I'll use it every day"])
        for span in opt + heavy: self.assertIn(span, chat)

    def test_no_weight_or_verdict_keys(self):
        out = extract.extract_case(RECEIPT, ["Ana: I'm in."])
        self.assertFalse(set(out["answers"]) & extract.FORBIDDEN_KEYS)

    def test_combined_case_prefers_receipt_total(self):
        out = extract.extract_case(RECEIPT, ["Ana: We agreed $120, not $168."])
        self.assertEqual(out["answers"]["total"]["value"], 168.00)

    def test_live_budget_guard(self):
        os.environ["CLOUDFLARE_ACCOUNT_ID"] = "x"; os.environ["CLOUDFLARE_API_TOKEN"] = "x"
        os.environ["HAGGLE_MAX_EXTRACT_CALLS"] = "0"
        with self.assertRaises(extract.ExtractUnavailable):
            extract.extract(RECEIPT, dict(extract.RECEIPT_FIELDS))
        os.environ.pop("HAGGLE_MAX_EXTRACT_CALLS", None)

if __name__ == "__main__":
    unittest.main()

class DissectTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("CLOUDFLARE_ACCOUNT_ID", None); os.environ.pop("CLOUDFLARE_API_TOKEN", None)

    def test_dissect_fields_shape(self):
        f = extract.dissect_fields(["Ana: hi", "Ben: yo"])
        self.assertIn("vendor", f)
        for i in (0, 1):
            for cat in extract.CLAIM_CATEGORIES:
                self.assertIn(f"msg_{i}_{cat}", f)
                self.assertEqual(f[f"msg_{i}_{cat}"]["type"], "text")

    def test_dissect_mock_attaches_full_source_line(self):
        out = extract.dissect_case(RECEIPT, ["Ana: I'm out, not paying for this.", "Ben: I'll pay my share."])
        self.assertEqual(out["source"], "mock")
        cats = {(c["message_index"], c["category"]) for c in out["claims"]}
        self.assertEqual(cats, {(0, "opt_out"), (1, "promise")})
        for c in out["claims"]:
            self.assertEqual(c["source_line"], ["Ana: I'm out, not paying for this.", "Ben: I'll pay my share."][c["message_index"]])

    def test_dissect_gate_drops_fragments(self):
        os.environ["CLOUDFLARE_ACCOUNT_ID"] = "x"; os.environ["CLOUDFLARE_API_TOKEN"] = "x"
        chat = ["Ana: I'm out, not paying for this.", "Ben: Looks right to me."]
        fake = {"source": "clairic", "model": extract.MODEL, "answers": {
            "msg_0_opt_out": {"value": "I", "confidence": 0.02},                    # fragment: dropped
            "msg_0_promise": {"value": "I'm out", "confidence": 0.30},              # verbatim but wrong category: kept (gate is presence, not truth)
            "msg_1_dispute": {"value": "hallucinated quote", "confidence": 0.60},   # not in message: dropped
        }}
        orig = extract.extract
        extract.extract = lambda state, fields: fake
        try:
            out = extract.dissect_case(RECEIPT, chat)
        finally:
            extract.extract = orig
        cats = {(c["message_index"], c["category"]) for c in out["claims"]}
        self.assertEqual(cats, {(0, "promise")})
        self.assertEqual(out["claims"][0]["source_line"], chat[0])

    def test_dissect_no_forbidden_keys(self):
        out = extract.dissect_case(RECEIPT, ["Ana: I'm in."])
        self.assertFalse(set(out["raw_answers"]) & extract.FORBIDDEN_KEYS)

class SelectTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("CLOUDFLARE_ACCOUNT_ID", None); os.environ.pop("CLOUDFLARE_API_TOKEN", None)

    def test_select_fields_shape(self):
        f = extract.select_fields(["Ana: hi", "Ben: yo"])
        self.assertIn("total", f)
        self.assertIn("msg_0_statement", f)
        self.assertIn("msg_1_statement", f)
        self.assertEqual(f["msg_0_statement"]["type"], "text")

    def test_select_mock_skips_bare_assent(self):
        out = extract.select_case(RECEIPT, ["Ana: Looks right to me.", "Ben: I'll pay my share."])
        idx = [s["message_index"] for s in out["statements"]]
        self.assertEqual(idx, [1])
        self.assertEqual(out["statements"][0]["source_line"], "Ben: I'll pay my share.")

    def test_select_gate_drops_fragments_and_hallucinations(self):
        os.environ["CLOUDFLARE_ACCOUNT_ID"] = "x"; os.environ["CLOUDFLARE_API_TOKEN"] = "x"
        chat = ["Ana: I'm out, not paying for this.", "Ben: Looks right to me."]
        fake = {"source": "clairic", "model": extract.MODEL, "answers": {
            "msg_0_statement": {"value": "not paying for this", "confidence": 0.5},
            "msg_1_statement": {"value": "made up words", "confidence": 0.6},
        }}
        orig = extract.extract
        extract.extract = lambda state, fields: fake
        try:
            out = extract.select_case(RECEIPT, chat)
        finally:
            extract.extract = orig
        self.assertEqual(len(out["statements"]), 1)
        self.assertEqual(out["statements"][0]["message_index"], 0)
        self.assertEqual(out["statements"][0]["source_line"], chat[0])
        self.assertEqual(out["statements"][0]["quote"], "not paying for this")

    def test_select_no_forbidden_keys(self):
        out = extract.select_case(RECEIPT, ["Ana: I'm in."])
        self.assertFalse(set(out["raw_answers"]) & extract.FORBIDDEN_KEYS)
