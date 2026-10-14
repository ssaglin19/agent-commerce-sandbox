"""Buyer-wallet path: the buyer approves the hold in PayPal, then the court rules.
start() negotiates a price and creates an AUTHORIZE order that needs buyer approval.
finish() runs only for a token we issued, once, and authorizes the approved order."""
import threading, time
from . import flow, negotiation, paypal, llm

_PENDING = {}
_lock = threading.Lock()
TTL = 3600

def start(base_url, scenario="happy", pp=None):
    pp = pp or paypal.client()
    if not hasattr(pp, "create_approval_order"): raise RuntimeError("wallet approval not supported by this client")
    deal = negotiation.run()
    if deal.agreed is None: return {"error": "No deal. Nothing created."}
    ret = f"{base_url}/wallet/return?scenario={scenario}"
    oid, url = pp.create_approval_order(deal.agreed, deal.item, ret, f"{base_url}/wallet/cancel")
    with _lock:
        now = time.time()
        for k in [k for k, v in _PENDING.items() if now - v["t"] > TTL]: del _PENDING[k]
        if len(_PENDING) >= 50: _PENDING.pop(next(iter(_PENDING)))
        _PENDING[oid] = {"deal": deal, "scenario": scenario, "t": now}
    return {"mode": pp.mode, "order": oid, "approve_url": url, "agreed": deal.agreed, "turns": deal.turns}

def finish(token, pp=None):
    pp = pp or paypal.client()
    with _lock:
        pend = _PENDING.pop(token, None)  # single use; unknown or reused tokens are refused
    if not pend: return {"error": "Unknown or already used approval token."}
    deal, scenario = pend["deal"], pend["scenario"]
    chat = flow.SCENARIOS.get(scenario, flow.CHAT)
    out = {"mode": pp.mode, "ai": {"provider": llm.provider()}, "scenario": scenario, "item": deal.item, "turns": deal.turns,
           "agreed": deal.agreed, "chat": chat, "steps": ["Buyer approved in PayPal"], "ids": {}, "path": "wallet"}
    ai0 = llm.STATS["ok"]
    try:
        auth = pp.authorize(token)
        flow.settle(pp, out, deal.agreed, token, auth, flow.PEOPLE, chat, ai0)
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return out
