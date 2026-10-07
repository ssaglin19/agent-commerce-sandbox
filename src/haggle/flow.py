"""End-to-end court session: haggle -> hold -> judge -> capture or void -> splits."""
from . import negotiation, judge, paypal

PEOPLE = ["Ana", "Ben", "Cam", "Dee"]
CHAT = [{"who": "Ana", "text": "I'll use the espresso machine every day"},
        {"who": "Ben", "text": "I'll skip most mornings, barely drinking coffee"},
        {"who": "Cam", "text": "I'm in for an even split"},
        {"who": "Dee", "text": "Just a sip on weekends for me"}]
CHAT_BAILOUT = [{"who": "Ana", "text": "At $168 I'm out, not paying for this"},
                {"who": "Ben", "text": "Same. Cancel it, I'm out"},
                {"who": "Cam", "text": "I'm still in"},
                {"who": "Dee", "text": "Not paying, this was a bad idea"}]
SCENARIOS = {"happy": CHAT, "void": CHAT_BAILOUT}

def hold(pp, amount, desc):
    """Place the hold. Real sandbox uses the test-card route (no buyer login); mock uses create+authorize."""
    if hasattr(pp, "pay_with_test_card"):
        oid, auth, status = pp.pay_with_test_card(amount, desc)
        if not auth: raise RuntimeError(f"order {oid} not authorized (status {status})")
        return oid, auth
    oid = pp.create_order(amount, desc)
    return oid, pp.authorize(oid)

def run_session(people=PEOPLE, chat=None, pp=None, scenario="happy", **kw):
    chat = chat or SCENARIOS.get(scenario, CHAT)
    pp = pp or paypal.client()
    deal = negotiation.run(**kw)
    out = {"mode": pp.mode, "scenario": scenario, "item": deal.item, "turns": deal.turns,
           "agreed": deal.agreed, "chat": chat, "steps": [], "ids": {}}
    if deal.agreed is None:
        out["steps"].append("No deal. Nothing authorized."); return out
    try:
        oid, auth = hold(pp, deal.agreed, deal.item)
        out["ids"].update(order=oid, authorization=auth)
        out["steps"].append(f"Funds held (authorized) order {oid}")
        ruling = judge.rule(deal.agreed, people, chat, receipt={"order": oid, "auth": auth, "total": deal.agreed})
        out["ruling"] = ruling
        if ruling["decision"] == "void":
            pp.void(auth); out["steps"].append("Court voided the hold. Nobody pays."); out["payouts"] = []
            return out
        cap = pp.capture(auth); out["ids"]["capture"] = cap; out["steps"].append(f"Captured {cap}")
        out["payouts"] = pp.payout([{"to": f"{p.lower()}@example.com", "amount": a} for p, a in ruling["shares"].items()])
        out["steps"].append("Split payout requests submitted; delivery is not confirmed")
    except Exception as e:  # show the failure in the UI instead of a blank page
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        if out["ids"].get("authorization") and "capture" not in out["ids"]:
            try: pp.void(out["ids"]["authorization"]); out["steps"].append("Error, so the hold was voided.")
            except Exception: pass
    return out
