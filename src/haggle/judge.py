"""Judge reads the receipt plus the group chat argument and rules who owes what."""
import json, re
from . import llm

def split_even(total, people):
    cents = round(total * 100); base, extra = divmod(cents, len(people))
    return {p: (base + (1 if i < extra else 0)) / 100 for i, p in enumerate(people)}

def rule(total, people, chat, receipt=None):
    """chat: list of {who, text}. Returns {shares, verdict}. Rule-based fallback:
    people who say 'skip'/'not paying' owe less ('light'); heavy claimers owe more.
    Shares always sum exactly to total."""
    verdict = None
    outs = {m["who"] for m in chat if any(w in m["text"].lower() for w in ("i'm out", "not paying", "cancel"))}
    if len(outs & set(people)) * 2 >= len(people):
        return {"decision": "void", "shares": {p: 0.0 for p in people},
                "verdict": f"{len(outs)} of {len(people)} walked out. Court voids the hold, nobody pays."}
    txt = llm.complete(
        "You are a gruff judge. Read the chat and return JSON {\"weights\": {name: number}, \"verdict\": str}.",
        json.dumps({"total": total, "people": people, "chat": chat, "receipt": receipt}), 300)
    weights = None
    if txt:
        try:
            m = re.search(r"\{.*\}", txt, re.S); j = json.loads(m.group(0))
            weights = {p: float(j["weights"][p]) for p in people}; verdict = j.get("verdict")
        except Exception:
            weights = None
    if not weights:
        weights = {p: 1.0 for p in people}
        for m in chat:
            t = m["text"].lower(); w = m["who"]
            if w in weights and ("skip" in t or "barely" in t or "just a sip" in t): weights[w] = 0.5
            if w in weights and ("every day" in t or "i'll hog" in t or "using it most" in t): weights[w] = 1.5
        verdict = "Court rules by use: lighter users pay less, heavy users pay more."
    s = sum(weights.values()); cents = {p: int(total * 100 * weights[p] / s) for p in people}
    rem = round(total * 100) - sum(cents.values())
    for p in sorted(people, key=lambda p: -weights[p])[:max(rem, 0)]: cents[p] += 1
    return {"decision": "capture", "shares": {p: c / 100 for p, c in cents.items()}, "verdict": verdict}
