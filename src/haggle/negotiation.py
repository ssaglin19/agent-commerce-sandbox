"""Buyer (Statler) and seller (Waldorf) haggle in rounds until they meet or give up."""
from dataclasses import dataclass, field
from . import llm

BUYER_LINES = ["That price? Daylight robbery, and I've been robbed by experts.",
               "My group chat has seen better offers from a parking meter.",
               "Ha! You call that a discount? I call it a hostage note.",
               "Final offer. Okay, second-to-final. Okay, I'm still talking."]
SELLER_LINES = ["Cheap? You want cheap? Go find a dollar store, I sell quality!",
                "I'm losing money here. Lovely, isn't it?",
                "Nobody haggles like you. That is not a compliment.",
                "Fine, fine. Take it before my accountant wakes up."]

@dataclass
class Deal:
    item: str
    list_price: float
    buyer_target: float
    seller_floor: float
    turns: list = field(default_factory=list)
    agreed: float | None = None

def _say(role, persona, fallback, price, deal):
    text = llm.complete(
        f"You are {persona}, a crotchety heckler haggling over a group buy of {deal.item}. "
        "One short insulting sentence, then the price. No emojis.",
        f"Current price on table: ${price:.2f}. Your role: {role}.")
    return text or f"{fallback} ${price:.2f}."

def run(item="Group-buy espresso machine", list_price=200.0, buyer_target=165.0,
        seller_floor=168.0, max_rounds=8):
    """Alternating concessions. Deal closes when offers cross within 2%.
    Returns Deal with transcript in deal.turns (list of {who, text, price})."""
    d = Deal(item, list_price, buyer_target, seller_floor)
    ask, bid = list_price, buyer_target * 0.75
    for i in range(max_rounds):
        bid = min(bid + (buyer_target - bid) * 0.55 + 4, buyer_target)
        d.turns.append({"who": "Statler (buyer)", "price": round(bid, 2),
                        "text": _say("buyer", "Statler", BUYER_LINES[i % 4], bid, d)})
        if bid >= max(ask, seller_floor) * 0.98:
            d.agreed = round(max(bid, seller_floor), 2); return d
        ask = max(seller_floor, ask - (ask - seller_floor) * 0.45 - 2)
        d.turns.append({"who": "Waldorf (seller)", "price": round(ask, 2),
                        "text": _say("seller", "Waldorf", SELLER_LINES[i % 4], ask, d)})
        if ask <= bid * 1.02 and ask >= seller_floor:
            d.agreed = round(ask, 2); return d
    return d
