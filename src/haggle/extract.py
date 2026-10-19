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

CLAIM_CATEGORIES = ("opt_out", "heavy_use", "promise", "paid_claim", "dispute")
_DISSECT_INSTR = {
    "opt_out": "In message [{i}] of the group chat, quote the exact words where the speaker declines to pay or leaves the purchase, or null",
    "heavy_use": "In message [{i}] of the group chat, quote the exact words where the speaker claims they will use the item a lot, or null",
    "promise": "In message [{i}] of the group chat, quote the exact words where the speaker commits to pay their share, or null",
    "paid_claim": "In message [{i}] of the group chat, quote the exact words where the speaker claims they already paid, or null",
    "dispute": "In message [{i}] of the group chat, quote the exact words where the speaker disputes the price, the charge, or the agreement, or null",
}
# Presence gate: the model's value is only a presence signal. It counts only when it is a
# verbatim substring of that same message and at least _MIN_QUOTE chars (fragments like a
# speaker name or "I" were the Oct 19 whole-chat list failure mode). The claim record always
# carries the full source line attached by code; the model's quote is kept for audit, never
# used as evidence. A miscategorized but verbatim substring can still pass the gate: the gate
# reduces false positives, it does not prove categorization. Categories are not mutually
# exclusive; one message can carry several claims.
_MIN_QUOTE = 4


def dissect_fields(chat_lines):
    """Scalar per-message claim fields: one text field per message per claim category.

    Whole-chat list extraction failed on Oct 19 (fragment spans, wrong membership), so claims
    are asked one message at a time inside the same single call. Receipt scalars were correct
    18/18 in that run; that says nothing about categorical claim detection, which this shape
    still has to prove against the same six cases."""
    fields = dict(RECEIPT_FIELDS)
    for i in range(len(chat_lines)):
        for cat in CLAIM_CATEGORIES:
            fields[f"msg_{i}_{cat}"] = {"type": "text", "instructions": _DISSECT_INSTR[cat].format(i=i)}
    return fields


def _mock_dissect(chat_lines):
    """Deterministic per-message classifier with the dissect output shape, for offline tests."""
    pats = {
        "opt_out": r"(i'm out|not paying|count me out)",
        "heavy_use": r"(every day|using it most|i'll hog|daily)",
        "promise": r"(i'm in|i'll pay|put me down|my share)",
        "paid_claim": r"(already paid|i paid for|i've paid|paid for everyone)",
        "dispute": r"(never agreed|didn't agree|wrong price|was \$|should be \$|we agreed \$|dispute)",
    }
    claims = []
    for i, line in enumerate(chat_lines):
        for cat, pat in pats.items():
            if re.search(pat, line, re.IGNORECASE):
                claims.append({"message_index": i, "speaker": line.split(":", 1)[0].strip(),
                               "category": cat, "source_line": line, "quote": line, "confidence": 1.0})
    return claims


def dissect_case(receipt_text, chat_lines):
    """One bounded call: receipt scalars plus per-message claim detection with a verbatim gate.

    Output: receipt fields, and claims with the full source line attached by code. Claims are
    evidence for the judge, not verdicts; contradictions stay attached to their source message.
    Returns raw per-field answers alongside so persisted fixtures keep the model's own output."""
    numbered = "\n".join(f"[{i}] {line}" for i, line in enumerate(chat_lines))
    state = f"RECEIPT:\n{receipt_text}\n\nGROUP CHAT:\n{numbered}"
    live = bool(os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN"))
    if not live:
        mock_ans = _mock(state, RECEIPT_FIELDS)
        return {"source": "mock", "model": None,
                "receipt": {k: mock_ans.get(k) for k in RECEIPT_FIELDS},
                "claims": _mock_dissect(chat_lines), "raw_answers": mock_ans}
    out = extract(state, dissect_fields(chat_lines))
    receipt = {k: out["answers"].get(k) for k in RECEIPT_FIELDS}
    claims = []
    for i, line in enumerate(chat_lines):
        speaker = line.split(":", 1)[0].strip()
        for cat in CLAIM_CATEGORIES:
            a = out["answers"].get(f"msg_{i}_{cat}") or {}
            q = (a.get("value") or "").strip()
            if q and len(q) >= _MIN_QUOTE and q in line and q.rstrip(": ").strip() != speaker:
                claims.append({"message_index": i, "speaker": speaker, "category": cat,
                               "source_line": line, "quote": q, "confidence": a.get("confidence")})
    return {"source": out["source"], "model": out.get("model"), "receipt": receipt,
            "claims": claims, "raw_answers": out["answers"]}


def extract_case(receipt_text, chat_lines):
    """One bounded call covering receipt fields and chat claims for a single case."""
    chat_text = "\n".join(chat_lines)
    state = f"RECEIPT:\n{receipt_text}\n\nGROUP CHAT:\n{chat_text}"
    return extract(state, dict(RECEIPT_FIELDS, **CHAT_FIELDS))


def select_fields(chat_lines):
    """Scalar per-message statement selection: one text field per message, no category labels.

    Oct 19 stage after dissection: Clairic picks WHAT each speaker explicitly said
    about paying, usage, price or the agreement; labeling and weighing stay with the judge.
    Categories steered the model into over-labeling, so this schema asks only for the
    statement itself, verbatim, or null."""
    fields = dict(RECEIPT_FIELDS)
    for i in range(len(chat_lines)):
        fields[f"msg_{i}_statement"] = {"type": "text", "instructions":
            f"In message [{i}] of the group chat, quote the exact words where the speaker states "
            "what they will pay, how much they will use the item, or what the price or agreement "
            "is, or null if the message states none of these"}
    return fields


def _mock_select(chat_lines):
    """Deterministic relevance pick with the select output shape, for offline tests."""
    pat = (r"(i'm out|not paying|count me out|every day|using it most|i'll hog|daily|i'm in|"
           r"i'll pay|put me down|my share|already paid|i paid for|i've paid|paid for everyone|"
           r"never agreed|didn't agree|wrong price|was \$|should be \$|we agreed \$|dispute|"
           r"sip|weekends|the price|the total)")
    return [{"message_index": i, "speaker": line.split(":", 1)[0].strip(),
             "source_line": line, "quote": line, "confidence": 1.0}
            for i, line in enumerate(chat_lines) if re.search(pat, line, re.IGNORECASE)]


def select_case(receipt_text, chat_lines):
    """One bounded call: receipt scalars plus per-message statement selection, no labels.

    Statements keep the full source line attached by code; the model's quote must pass the
    same verbatim gate as dissection. A selected statement is what a speaker SAID, not a
    fact: contradictions and overclaims stay attributed to their speaker for the judge.
    Returns raw per-field answers alongside so persisted fixtures keep the model's output."""
    numbered = "\n".join(f"[{i}] {line}" for i, line in enumerate(chat_lines))
    state = f"RECEIPT:\n{receipt_text}\n\nGROUP CHAT:\n{numbered}"
    live = bool(os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN"))
    if not live:
        mock_ans = _mock(state, RECEIPT_FIELDS)
        return {"source": "mock", "model": None,
                "receipt": {k: mock_ans.get(k) for k in RECEIPT_FIELDS},
                "statements": _mock_select(chat_lines), "raw_answers": mock_ans}
    out = extract(state, select_fields(chat_lines))
    receipt = {k: out["answers"].get(k) for k in RECEIPT_FIELDS}
    statements = []
    for i, line in enumerate(chat_lines):
        a = out["answers"].get(f"msg_{i}_statement") or {}
        q = (a.get("value") or "").strip()
        speaker = line.split(":", 1)[0].strip()
        if q and len(q) >= _MIN_QUOTE and q in line and q.rstrip(": ").strip() != speaker:
            statements.append({"message_index": i, "speaker": speaker, "source_line": line,
                               "quote": q, "confidence": a.get("confidence")})
    return {"source": out["source"], "model": out.get("model"), "receipt": receipt,
            "statements": statements, "raw_answers": out["answers"]}
