# Devpost submission text (draft)

## Name
Haggle Court

## Tagline
Two heckling bots haggle the price. Everyone approves their share. PayPal holds the money, and the group either buys or unwinds cleanly.

## Inspiration
Group buys die in the group chat. Everyone argues about price, half the group drops out, and nobody ever pays. We wanted the argument and the money to live in one place, and wanted it to be funny.

## What it does
One project, two parts: Haggle Court (the negotiation) and Pool (the settlement).

Statler (buyer bot) and Waldorf (seller bot) haggle the price of a group buy, trading insults each turn. The agreed price becomes a PayPal order with intent AUTHORIZE, so the funds are held, not taken. A judge bot reads the PayPal receipt and the group chat, then rules. If the group is in, it captures the order and works out each person's share, and PayPal Payouts sends the splits. If half the group or more says they are out, it voids the authorization and nobody is charged. A web page shows the argument live, with the PayPal IDs and the verdict.

Pool turns the agreed price into a group-funded purchase. Participant agents review the terms, but only a human approval tied to the exact terms counts, and any change clears all approvals. The coordinator holds each person's share through PayPal, asks for a final approval, captures, buys, and returns the remainder through Payouts. In the failure demo one capture fails: the coordinator stops, records the partial result, refunds the captures that went through and voids the other holds, and never claims everyone paid. Venmo is shown as a labeled simulation because its sandbox has no hold step.

## How we built it
Python standard library, no framework. A negotiation loop for the two bots, a judge that reads the order and chat, a PayPal client with a real sandbox implementation and a mock with the same interface, a small HTTP server and one-page UI, and a webhook receiver. PayPal APIs: OAuth2, Orders v2 (create, authorize, capture), Payments v2 (void, refund), and Payouts. The coordinator is an explicit state machine with an event log that deduplicates retries. Unit tests run in mock mode.

## Challenges
A plain Orders authorize needs buyer approval in a browser, which breaks an automated agent flow. In the sandbox we use a test card payment source so the hold happens without a login, and we kept the approval step as the real-world path.

## Accomplishments
A full hold, judge, capture or void, payout cycle running against the live PayPal sandbox with real IDs, and a void path that leaves no charge.

## What we learned
Authorize-then-decide fits agent commerce well: an agent can commit to a price without moving money until a second agent signs off.

## What's next
Buyer wallet approval step, LLM-written banter, webhook-driven status updates, and multi-seller bidding.

## Built with
Python, PayPal Orders v2, PayPal Payments v2, PayPal Payouts, PayPal webhooks

## Links
- Code (MIT): https://github.com/ssaglin19/agent-commerce-sandbox
- Video: (add after upload)
