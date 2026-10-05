"""PayPal sandbox client (Orders v2 authorize/capture, Payments v2 void, Payouts).
No credentials -> MockPayPal with the same interface so the demo runs offline.
Credentials come from env PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET (sandbox only)."""
import base64, json, os, urllib.request, uuid

BASE = "https://api-m.sandbox.paypal.com"

class MockPayPal:
    mode = "mock"
    def __init__(self): self.orders = {}
    def create_order(self, amount, desc):
        oid = "MOCK-" + uuid.uuid4().hex[:12].upper()
        self.orders[oid] = {"status": "CREATED", "amount": amount}; return oid
    def pay_with_test_card(self, amount, desc, **kw):
        oid = self.create_order(amount, desc); return oid, self.authorize(oid), "COMPLETED"
    def authorize(self, oid):
        self.orders[oid]["status"] = "AUTHORIZED"; return "AUTH-" + oid[5:]
    def capture(self, auth_id):
        for o in self.orders.values(): o["status"] = "CAPTURED"
        return "CAP-" + auth_id[5:]
    def void(self, auth_id): return "VOIDED"
    def payout(self, items): return [{"to": i["to"], "amount": i["amount"], "status": "SUCCESS(mock)"} for i in items]

class SandboxPayPal:
    mode = "sandbox"
    def __init__(self, cid, secret): self.cid, self.secret, self._tok = cid, secret, None
    def _req(self, path, body=None, auth=None, method="POST"):
        h = {"Content-Type": "application/json", "PayPal-Request-Id": uuid.uuid4().hex}
        h["Authorization"] = auth or "Bearer " + self._token()
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        r = urllib.request.Request(BASE + path, data, h, method=method)
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.loads(resp.read() or b"{}")
    def _token(self):
        if not self._tok:
            basic = base64.b64encode(f"{self.cid}:{self.secret}".encode()).decode()
            h = {"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded"}
            r = urllib.request.Request(BASE + "/v1/oauth2/token", b"grant_type=client_credentials", h)
            with urllib.request.urlopen(r, timeout=30) as resp: self._tok = json.load(resp)["access_token"]
        return self._tok
    def create_order(self, amount, desc):
        return self._req("/v2/checkout/orders", {"intent": "AUTHORIZE", "purchase_units": [
            {"description": desc, "amount": {"currency_code": "USD", "value": f"{amount:.2f}"}}]})["id"]
    def pay_with_test_card(self, amount, desc, number="4111111111111111", expiry="2030-01", cvv="123"):
        """Sandbox-only: create an AUTHORIZE order paid by a test card (no buyer login).
        Returns (order_id, authorization_id or None, raw_status)."""
        r = self._req("/v2/checkout/orders", {"intent": "AUTHORIZE",
            "purchase_units": [{"description": desc, "amount": {"currency_code": "USD", "value": f"{amount:.2f}"}}],
            "payment_source": {"card": {"number": number, "expiry": expiry, "security_code": cvv, "name": "Test Buyer",
                "billing_address": {"address_line_1": "1 Main St", "admin_area_2": "San Jose", "admin_area_1": "CA",
                                    "postal_code": "95131", "country_code": "US"}}}})
        try: auth = r["purchase_units"][0]["payments"]["authorizations"][0]["id"]
        except (KeyError, IndexError): auth = None
        return r["id"], auth, r.get("status")
    def authorize(self, oid):
        r = self._req(f"/v2/checkout/orders/{oid}/authorize", b"{}")
        return r["purchase_units"][0]["payments"]["authorizations"][0]["id"]
    def capture(self, auth_id): return self._req(f"/v2/payments/authorizations/{auth_id}/capture", b"{}")["id"]
    def void(self, auth_id): self._req(f"/v2/payments/authorizations/{auth_id}/void", b"{}"); return "VOIDED"
    def payout(self, items):
        body = {"sender_batch_header": {"sender_batch_id": uuid.uuid4().hex, "email_subject": "Haggle Court split"},
                "items": [{"recipient_type": "EMAIL", "receiver": i["to"],
                           "amount": {"value": f"{i['amount']:.2f}", "currency": "USD"}} for i in items]}
        r = self._req("/v1/payments/payouts", body); return [{"batch": r["batch_header"]["payout_batch_id"]}]

def client():
    cid, sec = os.environ.get("PAYPAL_CLIENT_ID"), os.environ.get("PAYPAL_CLIENT_SECRET")
    return SandboxPayPal(cid, sec) if cid and sec else MockPayPal()
