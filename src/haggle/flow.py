"""End-to-end court session: haggle -> hold -> judge -> capture or void -> splits."""
import datetime
from . import negotiation, judge, paypal, llm, extract

RECEIPT_VENDOR = "Lakeshore Coffee Supply"

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
    ai0 = llm.STATS["ok"]
    deal = negotiation.run(**kw)
    out = {"mode": pp.mode, "ai": {"provider": llm.provider()}, "scenario": scenario, "item": deal.item, "turns": deal.turns,
           "agreed": deal.agreed, "chat": chat, "steps": [], "ids": {}}
    if deal.agreed is None:
        out["steps"].append("No deal. Nothing authorized."); return out
    try:
        oid, auth = hold(pp, deal.agreed, deal.item)
        settle(pp, out, deal.agreed, oid, auth, people, chat, ai0)
    except Exception as e:  # show the failure in the UI instead of a blank page
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        if out["ids"].get("authorization") and "capture" not in out["ids"]:
            try: pp.void(out["ids"]["authorization"]); out["steps"].append("Error, so the hold was voided.")
            except Exception: pass
    return out

def settle(pp, out, agreed, oid, auth, people, chat, ai0=0):
    """Judge, then capture or void, then request split payouts. Shared by the test-card and wallet paths."""
    out["ids"].update(order=oid, authorization=auth)
    out["steps"].append(f"Funds held (authorized) order {oid}")
    ruling = judge.rule(agreed, people, chat, receipt={"order": oid, "auth": auth, "total": agreed})
    out["ruling"] = ruling
    out["ai"]["model_calls_ok"] = llm.STATS["ok"] - ai0
    if ruling["decision"] == "void":
        pp.void(auth); out["steps"].append("Court voided the hold. Nobody pays."); out["payouts"] = []
        return out
    cap = pp.capture(auth); out["ids"]["capture"] = cap; out["steps"].append(f"Captured {cap}")
    read_receipt(out, agreed)
    out["payouts"] = pp.payout([{"to": f"{p.lower()}@example.com", "amount": a} for p, a in ruling["shares"].items()])
    out["steps"].append("Split payout requests submitted; delivery is not confirmed")
    return out

def read_receipt(out, agreed):
    """Read the merchant receipt back as evidence after capture.

    Clairic (receipt fields only, its validated role) when CLOUDFLARE_ACCOUNT_ID and
    CLOUDFLARE_API_TOKEN are set, otherwise the local parser; the source is shown. This is
    evidence, not money: the captured amount stays the amount of record, the judge still
    reads the full chat, and a mismatch only adds a warning line."""
    text = (f"Receipt from {RECEIPT_VENDOR}. Seller: {RECEIPT_VENDOR}. "
            f"Total: ${agreed:.2f}. Date: {datetime.date.today().isoformat()}.")
    try:
        r = extract.extract(text, dict(extract.RECEIPT_FIELDS))
    except extract.ExtractUnavailable as e:
        out["steps"].append(f"Receipt read skipped ({e}); the captured amount is unaffected.")
        return
    a = r["answers"]
    facts = {"vendor": (a.get("vendor") or {}).get("value"),
             "total": (a.get("total") or {}).get("value"),
             "date": (a.get("date") or {}).get("value"),
             "source": r["source"]}
    facts["matches_capture"] = facts["total"] == round(agreed, 2)
    out["receipt_facts"] = facts
    label = "Clairic" if r["source"] == "clairic" else "local parser"
    total = f"${facts['total']:.2f}" if isinstance(facts["total"], (int, float)) else "unknown total"
    note = "matches the captured amount" if facts["matches_capture"] else "MISMATCH vs the captured amount (captured amount stands)"
    out["steps"].append(f"Receipt read ({label}): {facts['vendor']}, {total}, {facts['date']} - {note}.")
