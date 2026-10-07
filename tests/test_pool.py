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

class Safety(unittest.TestCase):
    def ready(self, rail=None):
        p=C.Plan('x', 20000, session.PEOPLE)
        for m in p.members: C.approve(p,m['name'],5000,p.terms_hash())
        rails={'paypal':rail or R.MockPayPal(),'venmo':R.SimulatedRail('venmo')}
        C.fund(p,rails)
        return p,rails
    def test_amend_after_hold_rejected(self):
        p,r=self.ready()
        with self.assertRaises(C.PlanError): C.amend(p,22000)
    def test_approve_after_hold_rejected(self):
        p,r=self.ready()
        with self.assertRaises(C.PlanError): C.approve(p,'Ana',5000,p.terms_hash())
    def test_over_budget_before_capture(self):
        p,r=self.ready()
        with self.assertRaises(C.PlanError): C.purchase(p,r,True,20001)
        self.assertTrue(all(m['status']=='authorized' for m in p.members))
    def test_forged_approval_rejected(self):
        p=C.Plan('x',20000,session.PEOPLE);p.state='approved'
        for m in p.members:m['approval']={'hash':'stale','max':5000}
        with self.assertRaises(C.PlanError): C.fund(p,{})
    def test_payout_failure_is_not_complete(self):
        class Broken(R.MockPayPal):
            def payout(self,items):raise R.RailError('payout unavailable')
        p,r=self.ready(Broken());C.purchase(p,r,True,18840)
        self.assertEqual(p.state,'distribution_pending')
        self.assertTrue(all(m['status']=='captured' for m in p.members))
    def test_refund_failure_is_not_cancelled(self):
        class Broken(R.MockPayPal):
            def refund(self,cap):raise R.RailError('refund unavailable')
        p,r=self.ready(Broken());C.purchase(p,r,True,18840,sabotage='Cy')
        self.assertEqual(p.state,'compensation_pending')
    def test_mock_not_labeled_real(self):
        p,r=self.ready();self.assertTrue(all(not m['real'] for m in p.members))
    def test_bad_plan(self):
        with self.assertRaises(C.PlanError): C.Plan('x',-1,session.PEOPLE)
