"""Payment rails for Pool. PayPal sandbox (real), mock PayPal (offline), and a clearly labeled simulated adapter.
Credentials: env PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET (sandbox only). Money is in integer cents."""
import base64, json, os, urllib.request, urllib.error, uuid

BASE = "https://api-m.sandbox.paypal.com"

class RailError(Exception): pass

def usd(cents): return f"{cents/100:.2f}"

class MockPayPal:
    """Same interface as SandboxPayPal, no network. Tracks state so failures behave like the real API."""
    mode = "mock"
    def __init__(self): self.auths = {}; self.caps = {}
    def authorize(self, cents, desc):
        a = "AUTH-" + uuid.uuid4().hex[:10].upper(); self.auths[a] = {"cents": cents, "state": "CREATED"}
        return {"order": "MOCK-" + a[5:], "auth": a}
    def capture(self, auth):
        a = self.auths.get(auth)
        if not a or a["state"] != "CREATED": raise RailError(f"capture failed: authorization is {a and a['state']}")
        a["state"] = "CAPTURED"; c = "CAP-" + auth[5:]; self.caps[c] = a["cents"]; return c
    def void(self, auth):
        a = self.auths[auth]
        if a["state"] == "CAPTURED": raise RailError("cannot void a captured authorization")
        a["state"] = "VOIDED"; return "VOIDED"
    def refund(self, cap): return "REF-" + cap[4:]
    def payout(self, items): return "MOCKBATCH-" + uuid.uuid4().hex[:8].upper()

class SandboxPayPal:
    """Real PayPal sandbox: Orders v2 (AUTHORIZE with a test card, no buyer login), Payments v2 capture/void/refund, Payouts."""
    mode = "sandbox"
    def __init__(self, cid, secret): self.cid, self.secret, self._tok = cid, secret, None
    def _token(self):
        if not self._tok:
            basic = base64.b64encode(f"{self.cid}:{self.secret}".encode()).decode()
            r = urllib.request.Request(BASE + "/v1/oauth2/token", b"grant_type=client_credentials",
                {"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(r, timeout=30) as resp: self._tok = json.load(resp)["access_token"]
        return self._tok
    def _req(self, path, body):
        h = {"Content-Type": "application/json", "PayPal-Request-Id": uuid.uuid4().hex, "Authorization": "Bearer " + self._token()}
        r = urllib.request.Request(BASE + path, json.dumps(body).encode(), h, method="POST")
        try:
            with urllib.request.urlopen(r, timeout=30) as resp: return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise RailError(f"PayPal {e.code} on {path.split('/')[-1]}: {e.read()[:200].decode(errors='replace')}")
    def authorize(self, cents, desc):
        r = self._req("/v2/checkout/orders", {"intent": "AUTHORIZE",
            "purchase_units": [{"description": desc, "amount": {"currency_code": "USD", "value": usd(cents)}}],
            "payment_source": {"card": {"number": "4111111111111111", "expiry": "2030-01", "security_code": "123", "name": "Test Buyer",
                "billing_address": {"address_line_1": "1 Main St", "admin_area_2": "San Jose", "admin_area_1": "CA",
                                    "postal_code": "95131", "country_code": "US"}}}})
        try: auth = r["purchase_units"][0]["payments"]["authorizations"][0]["id"]
        except (KeyError, IndexError): raise RailError("no authorization returned (status %s)" % r.get("status"))
        return {"order": r["id"], "auth": auth}
    def capture(self, auth): return self._req(f"/v2/payments/authorizations/{auth}/capture", {})["id"]
    def void(self, auth): self._req(f"/v2/payments/authorizations/{auth}/void", {}); return "VOIDED"
    def refund(self, cap): return self._req(f"/v2/payments/captures/{cap}/refund", {})["id"]
    def payout(self, items):
        body = {"sender_batch_header": {"sender_batch_id": uuid.uuid4().hex, "email_subject": "Pool remainder"},
                "items": [{"recipient_type": "EMAIL", "receiver": i["to"],
                           "amount": {"value": usd(i["cents"]), "currency": "USD"}} for i in items]}
        return self._req("/v1/payments/payouts", body)["batch_header"]["payout_batch_id"]

class SimulatedRail:
    """Venmo / Cash App / Zelle stand-in. Nothing real happens; every id is prefixed SIM- and status is 'simulated'.
    Venmo sandbox needs a buyer web login and does not simulate holds; Cash App and Zelle have no open consumer collection API."""
    mode = "simulated"
    def __init__(self, name): self.name = name
    def authorize(self, cents, desc): return {"order": "SIM-" + uuid.uuid4().hex[:8].upper(), "auth": "SIM-HOLD-" + uuid.uuid4().hex[:8].upper()}
    def capture(self, auth): return "SIM-CAP-" + auth[-8:]
    def void(self, auth): return "SIM-RELEASED"
    def refund(self, cap): return "SIM-REFUND-" + cap[-8:]
    def payout(self, items): return "SIM-PAYOUT-" + uuid.uuid4().hex[:8].upper()

def paypal():
    cid, sec = os.environ.get("PAYPAL_CLIENT_ID"), os.environ.get("PAYPAL_CLIENT_SECRET")
    return SandboxPayPal(cid, sec) if cid and sec else MockPayPal()
