"""End-to-end court session: haggle -> authorize -> judge -> capture -> splits."""
from . import negotiation, judge, paypal

PEOPLE = ["Ana", "Ben", "Cam", "Dee"]
CHAT = [{"who": "Ana", "text": "I'll use the espresso machine every day"},
        {"who": "Ben", "text": "I'll skip most mornings, barely drinking coffee"},
        {"who": "Cam", "text": "I'm in for an even split"},
        {"who": "Dee", "text": "Just a sip on weekends for me"}]

def run_session(people=PEOPLE, chat=CHAT, pp=None, **kw):
    pp = pp or paypal.client()
    deal = negotiation.run(**kw)
    out = {"mode": pp.mode, "item": deal.item, "turns": deal.turns, "agreed": deal.agreed, "steps": []}
    if deal.agreed is None:
        out["steps"].append("No deal. Nothing authorized."); return out
    oid = pp.create_order(deal.agreed, deal.item); out["steps"].append(f"Order created {oid}")
    auth = pp.authorize(oid); out["steps"].append(f"Funds held (authorized) {auth}")
    ruling = judge.rule(deal.agreed, people, chat, receipt={"order": oid, "auth": auth, "total": deal.agreed})
    out["ruling"] = ruling
    cap = pp.capture(auth); out["steps"].append(f"Captured {cap}")
    out["payouts"] = pp.payout([{"to": f"{p.lower()}@example.com", "amount": a} for p, a in ruling["shares"].items()])
    out["steps"].append("Split requests sent")
    return out
