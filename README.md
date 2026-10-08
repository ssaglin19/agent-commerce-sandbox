# Haggle Court

Entry for the PayPal AI hackathon. Two heckling bots haggle a group buy, a judge bot reads the receipt and the group chat, rules who owes what, and PayPal sandbox payment requests go out. Sandbox only, no real money.

Concept and demo story: [docs/concept-haggle-court.md](docs/concept-haggle-court.md). Dated public-source notes on agent payments: [docs/market-notes.md](docs/market-notes.md).

## Status

Work in progress. A demo runs on Render in mock mode: https://haggle-court.onrender.com (free tier, sleeps when idle). The sandbox demo uses a test-card payment source, so buyer-wallet login and approval are not required for that path. Sandbox authorization, capture, void and payouts were verified in development, including group-purchase success and failure rollback. The separate PayPal-wallet checkout path still needs a Personal sandbox buyer to approve an order and is not wired into the demo UI. No keys are in this repo.

## Layout

- `src/haggle/` - Haggle Court: negotiation, judge, PayPal sandbox calls, server, web page
- `src/pool/` - group-funding coordinator
- `payments/` - pointer to `src/pool/`
- `tests/` - tests for haggle and pool
- `docs/` - concept and notes

## Run and test

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m haggle.server
```

Open http://localhost:8000 and /pool. GET /healthz returns health and payment mode.
The public free Render instance can take time to wake; a single failed fetch is not proof the service is down.

## Demo limits

- Banter is scripted by default. If a Google Cloud key is configured (`GOOGLE_SA_JSON` or `GOOGLE_APPLICATION_CREDENTIALS`), Gemini on Vertex AI writes the bot banter and suggests the judge's weights. Code computes every price and share (model text has digits stripped, weights are clamped). Any error or call cap (`HAGGLE_MAX_LLM_CALLS`, `HAGGLE_MAX_LLM_CALLS_PER_DAY`) falls back to scripted lines. `/healthz` and each run report which mode was used. The pool coordinator is deterministic rules.
- The canned group demo simulates human approval and merchant purchase. It is not a production human-authentication flow.
- Mock PayPal and simulated Venmo are never labeled real sandbox funding.
- A payout batch ID confirms submission, not delivery. Failed payouts stay distribution_pending; failed refunds/voids stay compensation_pending.
- Webhooks are bounded and deduplicated. Sandbox mode rejects unsigned events or a missing webhook ID. Mock receipts are unverified and never drive settlement. Live PayPal webhook delivery is still untested.
- The current event log is in memory, not a durable idempotency or recovery ledger. Do not use this demo with real funds.
