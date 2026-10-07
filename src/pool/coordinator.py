"""Pool coordinator: an application-controlled group-funding workflow (not one atomic transaction).

States: proposed -> approved -> funding_pending -> ready -> purchasing -> distributing -> complete
        with failed -> compensating -> cancelled on any capture or funding failure.
Per-contribution status: pending, authorized, captured, refunded, released, failed. Each contribution is also tagged
real (PayPal sandbox) or simulated (labeled adapter); a simulated credit is never counted as funding."""
import hashlib, json, time

class PlanError(Exception): pass

def split_cents(total, n):
    base, extra = divmod(total, n)
    return [base + (1 if i < extra else 0) for i in range(n)]

class Plan:
    def __init__(self, item, total_cents, people, deadline="2026-11-01", cancel_rule="void holds, refund captures"):
        if not people or not isinstance(total_cents, int) or total_cents <= 0:
            raise PlanError("positive integer total and participants required")
        if len({p["name"] for p in people}) != len(people):
            raise PlanError("participant names must be unique")
        shares = split_cents(total_cents, len(people))
        self.item, self.total, self.deadline, self.cancel_rule, self.version = item, total_cents, deadline, cancel_rule, 1
        self.state = "proposed"
        self.members = [{"name": p["name"], "email": p["email"], "rail": p["rail"], "share": s,
                         "approval": None, "status": "pending", "order": None, "auth": None, "capture": None,
                         "refund": None, "real": p["rail"] == "paypal", "note": ""} for p, s in zip(people, shares)]
        self.log, self.seen, self.result = [], set(), {}
    def terms_hash(self):
        core = [self.item, self.total, self.deadline, self.cancel_rule, self.version, [(m["name"], m["share"]) for m in self.members]]
        return hashlib.sha256(json.dumps(core).encode()).hexdigest()[:12]
    def event(self, kind, who="coordinator", detail="", key=None):
        if key and key in self.seen: return False          # retries and duplicate notifications are deduplicated
        if key: self.seen.add(key)
        self.log.append({"t": len(self.log) + 1, "kind": kind, "who": who, "detail": detail, "state": self.state}); return True
    def set_state(self, s, why=""):
        self.state = s; self.event("state", detail=f"{s} {why}".strip())
    def to_dict(self):
        return {"item": self.item, "total": self.total, "state": self.state, "version": self.version, "hash": self.terms_hash(),
                "members": self.members, "log": self.log, "result": self.result}

def propose(plan, agents):
    """Participant agents exchange terms. Agent agreement is not authorization: only a human approval object is."""
    plan.event("proposal", detail=f"{plan.item}, ${plan.total/100:.2f}, deadline {plan.deadline}, cancel rule: {plan.cancel_rule}")
    for a in agents:
        line = a.review(plan)
        plan.event("agent", a.name + "'s agent", line)

def approve(plan, name, max_cents, plan_hash):
    """Record a human approval scoped to exact terms. Rejects a stale hash or a max below the share."""
    if plan.state not in ("proposed", "approved"): raise PlanError("approvals are closed after funding starts")
    m = next((x for x in plan.members if x["name"] == name), None)
    if not m: raise PlanError("unknown participant")
    if plan_hash != plan.terms_hash(): raise PlanError("approval is for different terms; plan changed")
    if max_cents < m["share"]: raise PlanError("approved maximum is below the share")
    m["approval"] = {"max": max_cents, "hash": plan_hash}
    plan.event("approval", name, f"approved ${m['share']/100:.2f} (max ${max_cents/100:.2f}) on terms {plan_hash}", key=f"appr:{name}:{plan_hash}")
    if all(x["approval"] for x in plan.members) and plan.state == "proposed": plan.set_state("approved", "all humans approved")

def amend(plan, new_total):
    """Any change to terms voids existing approvals; agents cannot change amounts after approval."""
    if plan.state not in ("proposed", "approved"): raise PlanError("cannot amend after funding starts")
    if not isinstance(new_total, int) or new_total <= 0: raise PlanError("positive integer total required")
    plan.total, plan.version = new_total, plan.version + 1
    for m, s in zip(plan.members, split_cents(new_total, len(plan.members))): m["share"], m["approval"] = s, None
    plan.state = "proposed"; plan.event("amend", detail=f"terms changed to ${new_total/100:.2f}; all approvals cleared")

def fund(plan, rails):
    if plan.state != "approved": raise PlanError("funding needs an approved plan")
    if any(not isinstance(m["approval"], dict) or m["approval"].get("hash") != plan.terms_hash()
           or m["approval"].get("max", 0) < m["share"] for m in plan.members):
        raise PlanError("current human approvals required for every share")
    plan.set_state("funding_pending")
    for m in plan.members:
        m["real"] = rails[m["rail"]].mode == "sandbox"
        try:
            r = rails[m["rail"]].authorize(m["share"], f"Pool: {plan.item} share for {m['name']}")
            m["order"], m["auth"], m["status"] = r["order"], r["auth"], "authorized"
            plan.event("hold", m["name"], f"${m['share']/100:.2f} held ({m['rail']}{'' if m['real'] else ', SIMULATED'}) auth {r['auth']}", key=f"auth:{r['auth']}")
        except Exception as e:
            m["status"], m["note"] = "failed", str(e)
            plan.event("error", m["name"], f"hold failed: {e}")
            return compensate(plan, rails, f"funding failed for {m['name']}")
    plan.set_state("ready", "every required share is held")
    return True

def purchase(plan, rails, final_approval, actual_cost, sabotage=None):
    """Needs an explicit final human approval. Captures one by one; the first failure stops and compensates.
    sabotage: name of a participant whose hold is voided out-of-band first, to demo a capture failure."""
    if plan.state != "ready": raise PlanError("not ready to purchase")
    if not final_approval: raise PlanError("final purchase approval required")
    if not isinstance(actual_cost, int) or not 0 < actual_cost <= plan.total:
        raise PlanError("purchase cost must be positive and within the approved total")
    plan.set_state("purchasing", "final approval given")
    if sabotage:
        m = next(x for x in plan.members if x["name"] == sabotage)
        rails[m["rail"]].void(m["auth"]); plan.event("external", m["name"], "hold lost outside the app (funds no longer available)")
    for m in plan.members:
        try:
            m["capture"] = rails[m["rail"]].capture(m["auth"]); m["status"] = "captured"
            plan.event("capture", m["name"], f"${m['share']/100:.2f} captured {m['capture']}", key=f"cap:{m['capture']}")
        except Exception as e:
            m["status"], m["note"] = "failed", str(e)
            plan.event("error", m["name"], f"capture failed: {e}")
            plan.set_state("failed", f"capture failed for {m['name']}; stopping, recording partial result")
            return compensate(plan, rails, "capture failure")
    plan.result["purchased"] = actual_cost
    plan.event("purchase", detail=f"purchase made for ${actual_cost/100:.2f} (simulated merchant)")
    return distribute(plan, rails, actual_cost)

def distribute(plan, rails, actual_cost):
    plan.set_state("distributing")
    rem = plan.total - actual_cost
    plan.result["remainder"] = rem
    if rem > 0:
        parts = split_cents(rem, len(plan.members))
        by = {}
        for m, c in zip(plan.members, parts):
            by.setdefault(m["rail"], []).append({"to": m["email"], "cents": c, "name": m["name"]})
        plan.result["payouts"] = []
        for rail, items in by.items():
            try:
                bid = rails[rail].payout(items)
                plan.result["payouts"].append({"rail": rail, "batch": bid, "real": rails[rail].mode == "sandbox", "items": [(i["name"], i["cents"]) for i in items]})
                plan.event("payout", detail=f"{rail}: ${sum(i['cents'] for i in items)/100:.2f} to {', '.join(i['name'] for i in items)} batch {bid}" + ("" if rails[rail].mode != "simulated" else " (SIMULATED)"))
            except Exception as e:
                plan.event("payout_error", detail=f"payout via {rail} failed: {e}")
    if any(e["kind"] == "payout_error" for e in plan.log):
        plan.result["summary"] = "Purchase captured, but remainder payout needs follow-up. Do not recapture."
        plan.set_state("distribution_pending", "one or more payout requests failed")
        return False
    plan.set_state("complete", "payout requests submitted; delivery is not yet confirmed")
    return True

def compensate(plan, rails, why):
    """Stop, then undo: void uncaptured holds, refund captures. Record exactly what happened; never claim everyone paid."""
    plan.set_state("compensating", why)
    unresolved = False
    for m in plan.members:
        try:
            if m["status"] == "captured":
                m["refund"] = rails[m["rail"]].refund(m["capture"]); m["status"] = "refunded"
                plan.event("refund", m["name"], f"captured ${m['share']/100:.2f} refunded {m['refund']}")
            elif m["status"] == "authorized":
                rails[m["rail"]].void(m["auth"]); m["status"] = "released"
                plan.event("release", m["name"], "hold voided, nothing charged")
        except Exception as e:
            unresolved = True
            m["note"] = str(e); plan.event("error", m["name"], f"compensation step failed, needs manual follow-up: {e}")
    plan.set_state("compensation_pending" if unresolved else "cancelled", why)
    plan.result["summary"] = ", ".join(f"{m['name']}: {m['status']}" for m in plan.members)
    return False
