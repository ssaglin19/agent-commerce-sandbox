# Devpost submission text (draft)

## Name
Haggle Court

## Tagline
Two heckling bots haggle the price. The demo simulates approvals for exact shares. PayPal holds the money, and the group either buys or unwinds cleanly.

## Inspiration
Group buys die in the group chat. Everyone argues about price, half the group drops out, and nobody ever pays. We wanted the argument and the money to live in one place, and wanted it to be funny.

## Note on the demo video
The video was recorded on Oct 7, 2026 against the live Gemini (Vertex AI) role. The public demo falls back to scripted lines whenever no key is configured or a call cap is reached, and the key is removed from the public demo on Oct 26, 2026. To run the live AI role, see "Try the live AI role yourself" in the README.

## What it does
One project, two parts: Haggle Court (the negotiation) and Pool (the settlement).

Statler (buyer bot) and Waldorf (seller bot) haggle the price of a group buy, trading insults each turn. The agreed price becomes a PayPal order with intent AUTHORIZE, so the funds are held, not taken. A rule-based judge reads the PayPal receipt and the group chat, then rules. If the group is in, it captures the order and works out each person's share, and PayPal Payouts submits the splits. If half the group or more says they are out, it voids the authorization and nobody is charged. A web page shows the argument live, with the PayPal IDs and the verdict.

Pool turns the agreed price into a group-funded purchase. Participant agents review the terms, but only a human approval tied to the exact terms counts, and any change clears all approvals. The coordinator holds each person's share through PayPal, asks for a final approval, captures, buys, and requests remainder payouts through Payouts. In the failure demo one capture fails: the coordinator stops, records the partial result, requests refunds for successful captures and voids the other holds, and never claims everyone paid. Payout or compensation failures remain pending for follow-up. Venmo is shown as a labeled simulation because its sandbox has no hold step.

## How we built it
Python standard library, no framework. A negotiation loop for the two bots, a rule-based judge that reads the order and chat (optionally Gemini on Vertex AI writes the banter and suggests judge weights; code computes all money and falls back to scripted on any error), a PayPal client with a real sandbox implementation and a mock with the same interface, a small HTTP server and one-page UI, and a signature-checking webhook receiver. Live webhook delivery remains unverified. PayPal APIs: OAuth2, Orders v2 (create, authorize, capture), Payments v2 (void, refund), and Payouts. The coordinator is an explicit state machine with an event log that deduplicates log keys (not a durable transaction retry ledger). 25 unit tests run in mock mode. Banter is scripted by default and settlement rules are deterministic, so the current build should not be described as LLM-driven. Merchant purchase and participant approvals are simulated in the demo.

## Challenges
A plain Orders authorize needs buyer approval in a browser, which breaks an automated agent flow. In the sandbox we use a test card payment source so the hold happens without a login, and we kept the approval step as the real-world path.

## Accomplishments
A full hold, judge, capture or void, payout cycle running against the live PayPal sandbox with real IDs, and a void path that leaves no charge.

## What we learned
Authorize-then-decide fits agent commerce well: an agent can commit to a price without moving money until a second agent signs off.

## What's next
Buyer wallet approval step, webhook-driven status updates, and multi-seller bidding.

## Built with
Python, PayPal Orders v2, PayPal Payments v2, PayPal Payouts, PayPal webhooks

## Links
- Code (MIT): https://github.com/ssaglin19/agent-commerce-sandbox
- Video: (add after upload)
