"""Clairic fact extraction (Cloudflare Workers AI, preview model @cf/cloudflare/clairic).

Scope: pull FACTS out of the receipt and the group chat as typed fields with verbatim
spans: what the receipt says, and what each participant explicitly claimed. The judge
still weighs those facts. Extraction output never contains weights, shares or verdicts;
it is evidence, not a ruling. Confidence scores are reported, never treated as truth
(the vendor-truncation-at-full-confidence failure is documented in Geeza's live check).

Providers, first match wins:
  1. Cloudflare Workers AI: CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN (env only, never repo).
  2. Mock: deterministic regex extraction with the same interface, so tests run offline.

Call budget: HAGGLE_MAX_EXTRACT_CALLS per process (default 10). Past the budget, or on any
API error, extract() raises ExtractUnavailable rather than silently falling back, so a live
run can never quietly become a mock run. Untrusted chat text is data: it is sent inside the
state document only, and any instructions inside it cannot change the requested fields.
"""
import json, os, re, urllib.request

MODEL = "@cf/cloudflare/clairic"
_calls = {"n": 0}

RECEIPT_FIELDS = {
    "vendor": {"type": "text", "instructions": "Seller or merchant name on the receipt"},
    "total": {"type": "number", "decimals": 2, "unit": "USD", "instructions": "Final amount charged"},
    "date": {"type": "date", "instructions": "Receipt date"},
}
CHAT_FIELDS = {
    "opt_outs": {"type": "list", "items": "text", "instructions": "Verbatim quotes of a person explicitly declining to pay or leaving the purchase"},
    "heavy_use_claims": {"type": "list", "items": "text", "instructions": "Verbatim quotes of a person claiming they will use the item a lot"},
    "payment_disputes": {"type": "list", "items": "text", "instructions": "Verbatim quotes disputing the price, the charge, or whether the group agreed"},
    "payment_promises": {"type": "list", "items": "text", "instructions": "Verbatim quotes of a person committing to pay their share"},
}
FORBIDDEN_KEYS = {"weights", "shares", "verdict", "decision"}

class ExtractUnavailable(Exception):
    pass

def _budget():
    try: return int(os.environ.get("HAGGLE_MAX_EXTRACT_CALLS", "10"))
    except ValueError: return 10

def _live(state, fields):
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID"); tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not acct or not tok: raise ExtractUnavailable("no Cloudflare credentials in env")
    if _calls["n"] >= _budget(): raise ExtractUnavailable("call budget reached")
    _calls["n"] += 1
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{MODEL}"
    body = json.dumps({"model": "clairic", "state": state, "fields": fields}).encode()
    req = urllib.request.Request(url, body, {"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = json.load(r)
    except Exception as e:
        raise ExtractUnavailable(f"api error: {e}")
    answers = (((raw or {}).get("result") or {}).get("answers"))
    if not isinstance(answers, dict): raise ExtractUnavailable("no answers in response")
    return answers

def _spans(text, pattern):
    return [{"value": m.group(0), "start": m.start()} for m in re.finditer(pattern, text, re.IGNORECASE)]

def _mock(state, fields):
    """Deterministic stand-in: same shape, regex spans. Numbers/dates read literally from the state."""
    out = {}
    for name, spec in fields.items():
        t = spec["type"]
        if t == "number":
            m = re.search(r"\$(\d[\d,]*\.\d{2})", state)
            out[name] = {"value": float(m.group(1).replace(",", "")) if m else None, "confidence": 1.0 if m else 0.0}
        elif t == "date":
            m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", state)
            out[name] = {"value": m.group(1) if m else None, "confidence": 1.0 if m else 0.0}
        elif t == "text":
            m = re.search(r"Seller:\s*([A-Z][A-Za-z0-9 &'-]{2,40})", state) or \
                re.search(r"\bfrom\s+([A-Z][A-Za-z0-9 &'-]{2,40})", state)
            out[name] = {"value": m.group(1).strip() if m else None, "confidence": 0.9 if m else 0.0}
        elif t == "list":
            pats = {
                "opt_outs": r"[A-Z][A-Za-z]+: [^.\n]*(?:i'm out|not paying|count me out)[^.\n]*",
                "heavy_use_claims": r"[A-Z][A-Za-z]+: [^.\n]*(?:every day|using it most|i'll hog|daily)[^.\n]*",
                "payment_disputes": r"[A-Z][A-Za-z]+: [^.\n]*(?:never agreed|didn't agree|wrong price|was \$|should be \$|we agreed \$|dispute)[^.\n]*",
                "payment_promises": r"[A-Z][A-Za-z]+: [^.\n]*(?:i'm in|i'll pay|put me down|my share)[^.\n]*",
            }
            out[name] = {"value": [s["value"] for s in _spans(state, pats.get(name, r"a^"))], "confidence": None}
        else:
            out[name] = {"value": None, "confidence": None}
    return out

def extract(state, fields):
    """Typed extraction for one state document. Live when credentialed, else mock.
    Raises ExtractUnavailable when a live run was requested (creds set) but fails or hits budget."""
    if os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN"):
        src, ans = "clairic", _live(state, fields)
    else:
        src, ans = "mock", _mock(state, fields)
    clean = {k: v for k, v in ans.items() if k not in FORBIDDEN_KEYS}
    return {"source": src, "model": MODEL if src == "clairic" else None, "answers": clean}

def extract_case(receipt_text, chat_lines):
    """One bounded call covering receipt fields and chat claims for a single case."""
    chat_text = "\n".join(chat_lines)
    state = f"RECEIPT:\n{receipt_text}\n\nGROUP CHAT:\n{chat_text}"
    return extract(state, dict(RECEIPT_FIELDS, **CHAT_FIELDS))
