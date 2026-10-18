#!/usr/bin/env python3
"""Register the Haggle Court webhook with the PayPal sandbox and print the webhook ID.

Run this once the sandbox app credentials are approved for local use:
    PAYPAL_CLIENT_ID=... PAYPAL_CLIENT_SECRET=... python3 scripts/register_webhook.py

Then set PAYPAL_WEBHOOK_ID on Render (Environment) with the printed ID and redeploy.
Credentials come from the environment only and are never printed.

--dry-run prints the request payload without calling PayPal.
"""
import base64, json, os, sys, urllib.request

BASE = "https://api-m.sandbox.paypal.com"
EVENTS = [
    "PAYMENT.CAPTURE.COMPLETED",
    "PAYMENT.CAPTURE.DENIED",
    "PAYMENT.PAYOUTS-ITEM.SUCCEEDED",
    "PAYMENT.PAYOUTS-ITEM.FAILED",
    "CHECKOUT.ORDER.APPROVED",
]


def token(cid, secret):
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req = urllib.request.Request(
        BASE + "/v1/oauth2/token", b"grant_type=client_credentials",
        {"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def call(path, tok, body=None, method=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data,
        {"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
        method=method or ("POST" if body is not None else "GET"))
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def main():
    hook_url = os.environ.get("HAGGLE_BASE_URL", "https://haggle-court.onrender.com").rstrip("/") + "/webhook"
    payload = {"url": hook_url, "event_types": [{"name": e} for e in EVENTS]}
    if "--dry-run" in sys.argv:
        print("DRY RUN - no PayPal call. Would ensure this webhook exists:")
        print(json.dumps(payload, indent=2))
        return 0
    cid, secret = os.environ.get("PAYPAL_CLIENT_ID"), os.environ.get("PAYPAL_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit("Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET (sandbox app) in the environment.")
    tok = token(cid, secret)
    existing = call("/v1/notifications/webhooks", tok).get("webhooks", [])
    for w in existing:
        if w.get("url") == hook_url:
            print("Already registered. PAYPAL_WEBHOOK_ID=" + w["id"])
            return 0
    created = call("/v1/notifications/webhooks", tok, payload)
    print("Registered. PAYPAL_WEBHOOK_ID=" + created["id"])
    print("Next: set PAYPAL_WEBHOOK_ID on Render (Environment), redeploy, then run the demo once and check the log for a verified PAYMENT.CAPTURE.COMPLETED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
