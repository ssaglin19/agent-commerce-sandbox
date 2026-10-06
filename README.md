# Haggle Court

Entry for the PayPal AI hackathon. Two heckling bots haggle a group buy, a judge bot reads the receipt and the group chat, rules who owes what, and PayPal sandbox payment requests go out. Sandbox only, no real money.

Concept and demo story: [docs/concept-haggle-court.md](docs/concept-haggle-court.md). Dated public-source notes on agent payments: [docs/market-notes.md](docs/market-notes.md).

## Status

Work in progress. A demo runs on Render in mock mode: https://haggle-court.onrender.com (free tier, sleeps when idle). PayPal sandbox token, order and payout calls work. Sandbox authorize needs a buyer approval, so a full pay-and-settle run is not finished. No keys are in this repo.

## Layout

- `src/haggle/` - Haggle Court: negotiation, judge, PayPal sandbox calls, server, web page
- `src/pool/` - group-funding coordinator
- `payments/` - pointer to `src/pool/`
- `tests/` - tests for haggle and pool
- `docs/` - concept and notes
