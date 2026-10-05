"""Smoke test against the real PayPal sandbox. Needs PAYPAL_CLIENT_ID/SECRET in env.
Steps: token, create AUTHORIZE order, (buyer approval is needed for authorize), report each step."""
import json, sys, urllib.error
from . import paypal

def step(name, fn):
    try:
        r = fn(); print(f"OK   {name}: {str(r)[:90]}"); return r
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]; print(f"FAIL {name}: HTTP {e.code} {body}"); return None
    except Exception as e:
        print(f"FAIL {name}: {type(e).__name__} {str(e)[:200]}"); return None

def main():
    pp = paypal.client()
    print("mode:", pp.mode)
    if pp.mode != "sandbox": sys.exit("no creds in env")
    step("oauth token", lambda: "got token" if pp._token() else None)
    oid = step("create order (AUTHORIZE)", lambda: pp.create_order(168.00, "Haggle Court group buy"))
    if oid: step("get order", lambda: pp._req(f"/v2/checkout/orders/{oid}", None, method="GET").get("status"))
    step("authorize (expected to need buyer approval)", lambda: pp.authorize(oid) if oid else None)
    step("payouts (empty-ish probe)", lambda: pp.payout([{"to": "sb-buyer@personal.example.com", "amount": 1.00}]))

if __name__ == "__main__": main()
