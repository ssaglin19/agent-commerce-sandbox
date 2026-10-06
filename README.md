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
