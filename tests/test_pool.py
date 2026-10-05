import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pool import coordinator as C, session, rails as R

class T(unittest.TestCase):
    def test_split_exact(self): self.assertEqual(sum(C.split_cents(20001, 4)), 20001)
    def test_happy(self):
        d = session.run("happy", R.MockPayPal())
        self.assertEqual(d["state"], "complete"); self.assertEqual(d["result"]["remainder"], 20000 - 18840)
        self.assertTrue(all(m["status"] == "captured" for m in d["members"]))
    def test_failure_compensates(self):
        d = session.run("failure", R.MockPayPal())
        self.assertEqual(d["state"], "cancelled")
        st = {m["name"]: m["status"] for m in d["members"]}
        self.assertEqual(st, {"Ana": "refunded", "Ben": "refunded", "Cy": "failed", "Dee": "released"})
    def test_stale_approval_rejected(self):
        p = C.Plan("x", 20000, session.PEOPLE); h = p.terms_hash(); C.amend(p, 22000)
        with self.assertRaises(C.PlanError): C.approve(p, "Ana", 5000, h)
    def test_no_final_approval(self):
        p = C.Plan("x", 20000, session.PEOPLE)
        for m in p.members: m["approval"] = 1
        p.state = "ready"
        with self.assertRaises(C.PlanError): C.purchase(p, {}, False, 100)
    def test_dedupe(self):
        p = C.Plan("x", 20000, session.PEOPLE)
        self.assertTrue(p.event("a", key="k")); self.assertFalse(p.event("a", key="k"))
    def test_max_below_share(self):
        p = C.Plan("x", 20000, session.PEOPLE)
        with self.assertRaises(C.PlanError): C.approve(p, "Ana", 4000, p.terms_hash())

class H(unittest.TestCase):
    def test_haggle_feeds_pool(self):
        d = session.run("happy", R.MockPayPal(), haggle=True)
        self.assertEqual(d["state"], "complete"); self.assertLessEqual(d["total"], 20000)

if __name__ == "__main__": unittest.main()
