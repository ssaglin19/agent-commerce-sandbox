"""Run a full demo session. Scenarios: 'happy' ($200 split four ways) and 'failure' (one capture fails, compensation)."""
from . import rails as R, coordinator as C, agents as A

PEOPLE = [
    {"name": "Ana", "email": "ana.pool.test@example.com", "rail": "paypal"},
    {"name": "Ben", "email": "ben.pool.test@example.com", "rail": "paypal"},
    {"name": "Cy", "email": "cy.pool.test@example.com", "rail": "paypal"},
    {"name": "Dee", "email": "dee.pool.test@example.com", "rail": "venmo"},
]

def run(scenario="happy", pp=None, haggle=False):
    """haggle=True: Statler and Waldorf (the Haggle Court bots) negotiate first, and their agreed price becomes the pool total."""
    pp = pp or R.paypal()
    rails = {"paypal": pp, "venmo": R.SimulatedRail("venmo")}
    item, total, chat = "Team offsite cabin", 20000, []
    if haggle:
        from haggle import negotiation
        deal = negotiation.run()
        if deal.agreed is not None: item, total = deal.item, int(round(deal.agreed * 100))
        chat = [(t.get("who", ""), t.get("text", "")) for t in getattr(deal, "turns", [])][:8] if hasattr(deal, "turns") else []
    plan = C.Plan(item, total, PEOPLE)
    for who, text in chat: plan.event("haggle", who, text)
    if haggle: plan.event("haggle", "Haggle Court", f"agreed price ${total/100:.2f} becomes the pool total")
    C.propose(plan, [A.Agent(p["name"], 5000) for p in PEOPLE])
    for p in PEOPLE: C.approve(plan, p["name"], 5000, plan.terms_hash())
    C.fund(plan, rails)
    if plan.state == "ready":
        C.purchase(plan, rails, final_approval=True, actual_cost=int(round(total * 0.942)), sabotage="Cy" if scenario == "failure" else None)
    d = plan.to_dict(); d.update(scenario=scenario, mode=pp.mode); return d
