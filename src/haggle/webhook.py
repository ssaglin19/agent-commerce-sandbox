"""Bounded webhook receipt log. Sandbox events require PayPal signature verification.
Mock receipts are explicitly unverified and never drive settlement."""
import json, os, threading
from . import paypal

EVENTS = []
_lock = threading.Lock()

def verify(event, headers):
    wid = os.environ.get("PAYPAL_WEBHOOK_ID")
    pp = paypal.client()
    if pp.mode != "sandbox": return False
    if not wid: return False
    fields = {"auth_algo": headers.get("PAYPAL-AUTH-ALGO"), "cert_url": headers.get("PAYPAL-CERT-URL"),
              "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"), "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
              "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME")}
    if not all(fields.values()): return False
    try:
        r = pp._req("/v1/notifications/verify-webhook-signature", dict(fields, webhook_id=wid, webhook_event=event))
        return r.get("verification_status") == "SUCCESS"
    except Exception:
        return False

def handle(body, headers):
    try:
        ev = json.loads(body)
        if not isinstance(ev, dict) or not isinstance(ev.get("id"), str) or not isinstance(ev.get("event_type"), str): return False
        if len(ev["id"]) > 128 or len(ev["event_type"]) > 128: return False
    except (ValueError, TypeError): return False
    sandbox = paypal.client().mode == "sandbox"
    verified = verify(ev, headers) if sandbox else False
    if sandbox and not verified: return False
    with _lock:
        if any(e["id"] == ev["id"] for e in EVENTS): return True
        EVENTS.append({"type": ev["event_type"], "id": ev["id"], "verified": verified})
        del EVENTS[:-50]
    return True
