# Haggle Court

Two crotchety bots haggle over a group buy while the real money rails run underneath. Statler (buyer) and Waldorf (seller) heckle each other down to a price. PayPal holds the funds, a judge bot reads the receipt and the group chat, then rules: capture and split the payments, or void the hold.

Built for the PayPal AI hackathon. MIT licensed.

## What happens

1. Statler and Waldorf negotiate a group-buy price, trading insults each turn.
2. The agreed price becomes a PayPal sandbox order with intent AUTHORIZE (funds held, not taken).
3. The judge bot reads the receipt and the group chat. If at least half the group says they are out, it rules **void**: the authorization is voided and nobody pays. Otherwise it rules **capture**.
4. On capture, the order is captured and split payments go out to each member through PayPal Payouts.
5. The web page shows the argument live, plus the PayPal IDs and the judge's verdict. Two buttons: happy path and void path.

## PayPal APIs used

- OAuth2 client credentials
- Orders v2: create (AUTHORIZE), authorize, capture
- Payments v2: void authorization
- Payouts: split payments
- Webhook receiver (`webhook.py`)

In the sandbox the hold uses a test card payment source, so no buyer login is needed.

## Run

```
python3 -m unittest discover tests
PYTHONPATH=src python3 -m haggle.server   # open http://localhost:8000
```

With no credentials it runs in mock mode (same interface, no network). For the real sandbox, copy `.env.example` to `.env` and set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` from a sandbox Merchant app at developer.paypal.com. Optional: `ANTHROPIC_API_KEY` makes the bots and judge use an LLM; otherwise they use scripted lines.

`PYTHONPATH=src python3 -m haggle.sandbox_check` runs a live check of auth, order, void, capture and payouts.

## Layout

- `src/haggle/` negotiation, judge, PayPal clients (real and mock), flow, web server and page, webhook
- `tests/` unit tests (mock mode)
- `docs/` notes

Keys are never committed (`.env` is gitignored).
