"""PayPal webhook receiver. Verifies signature via PayPal's verify-webhook-signature API when
PAYPAL_WEBHOOK_ID and sandbox creds are set; otherwise accepts and logs (dev only)."""
import json, os
from . import paypal

EVENTS = []  # recent events, newest last

def verify(body, headers):
    wid = os.environ.get("PAYPAL_WEBHOOK_ID")
    pp = paypal.client()
    if not wid or pp.mode != "sandbox": return True
    try:
        r = pp._req("/v1/notifications/verify-webhook-signature", {
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO"), "cert_url": headers.get("PAYPAL-CERT-URL"),
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"), "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME"), "webhook_id": wid,
            "webhook_event": json.loads(body)})
        return r.get("verification_status") == "SUCCESS"
    except Exception:
        return False

def handle(body, headers):
    if not verify(body, headers): return False
    ev = json.loads(body); EVENTS.append({"type": ev.get("event_type"), "id": ev.get("id")})
    del EVENTS[:-50]; return True
