# Agent-coordinated group purchases

Hackathon concept | October 2, 2026 | Proposed, not implemented

## The pitch

PayPal is the proposed payment intermediary for a group purchase. Each person's agent negotiates their share with the other agents, gathers that person's approval, and coordinates the final purchase and distributions. The group sees one plan and one payment status instead of chasing contributions across apps.

The demo shows the orchestration: agree on a purchase, commit shares, confirm funding, then buy and distribute any remainder. "Pool" describes the application's group ledger and proposed payment flow. It does not claim that PayPal offers an approved consumer escrow product.

## A small demo story

Four synthetic participants split a $200 purchase. Each approves a $50 maximum and the same purchase terms.

1. Participant agents exchange the item, total, shares, deadline and cancellation rule.
2. Each person reviews their exact contribution and approves. Agent agreement alone cannot authorize a payment.
3. The coordinator records approvals and funding status. PayPal sandbox authorizations can demonstrate a hold before capture where supported. Venmo uses supported sandbox checkout; any unverified hold/release step is visibly simulated.
4. When every required share is ready, the coordinator requests final purchase approval and executes the sandbox payment sequence. If a participant declines or the deadline passes, cancel the plan and void uncaptured authorizations; refund captured payments if needed.
5. Agents agree on the distribution ledger. Use PayPal sandbox Payouts where available and display per-item status; unsupported rail settlement remains simulated.

This is an application-controlled workflow. Separate authorizations, captures, a purchase and payouts are not one atomic transaction. Include a failure demo: one capture fails, and the coordinator stops, records the partial result and starts compensation rather than claiming everyone paid.

## Architecture proposal (judgment)

- **Participant agents:** propose shares, carry explicit owner approvals, report state.
- **Coordinator:** validates the agreed plan, tracks a group ledger and calls payment adapters. Agents cannot directly change amounts or destinations after approval.
- **Rail adapters:** PayPal sandbox first, Venmo sandbox checkout, and clearly labeled Cash App/Zelle fixtures.
- **Event log:** group ID, plan version, approval scope, payment IDs and status. Deduplicate retries and notifications. A notification is evidence to reconcile, not permission to debit an account.

Suggested states: `proposed -> approved -> funding_pending -> ready -> purchasing -> distributing -> complete`, with `cancelled`, `failed` and `compensating` paths. Track each contribution separately as `authorized`, `captured`, `simulated` or `unverified`; do not count a simulated credit as actual funding.

## Rails: verified documentation vs demo judgment

"Verified" below means supported by inspected public documentation, not tested in this repository. Negative findings mean not found in those documents, not proof that private programs cannot exist.

### PayPal and Venmo

**Verified:** PayPal Checkout supports separate authorization and capture. An authorization is a hold, not money already pooled in a merchant balance; capture is subject to risk and funds availability. [1]

Venmo is supported through PayPal merchant checkout for US buyers in USD. PayPal Payouts can send to Venmo recipients; live Payouts needs access approval and business-account setup. These are merchant checkout/payout interfaces, not a general consumer P2P or wallet-sweep API. No general consumer-balance-read interface was found in the inspected documentation. [2][3][4]

Venmo sandbox supports one-time checkout, app-switch/web-login and vault setup. It does not simulate subsequent vaulted purchases, settlement/disbursement, disputes, merchant reporting or the post-purchase feed/ledger. The separate PayPal Payouts guide documents a sandbox request and a Venmo recipient option; that is not proof of end-to-end Venmo settlement. [4][5]

**Demo judgment:** use actual PayPal sandbox authorization/capture where supported and actual Venmo sandbox checkout. Label Venmo hold/release or settlement steps as simulated unless separately verified. Do not imply one native API pools everyone's money and releases it atomically.

### Cash App

**Verified:** Cash App Pay exposes customer-approved merchant payments and an early-access payouts API. Direct API access requires partner approval, primarily for PSPs and selected ecommerce platforms. Payouts need a customer grant, an onboarded merchant and separately arranged funding to Block. No general consumer-balance-read interface was found. [6][7][8]

**Demo judgment:** use a simulated adapter. These merchant interfaces do not establish automatic collection from arbitrary consumer wallets.

### Zelle

**Verified:** Zelle has bank/network partnerships. J.P. Morgan and U.S. Bank document corporate disbursement APIs for eligible recipients' Zelle-linked bank accounts using email or phone. These prove bank-partner payout access, not a universal third-party consumer collection or balance-read API. No such collection/balance interface was found. [9][10][11]

**Demo judgment:** a synthetic bank-notification event can reconcile a contribution. A real version would need an authorized bank-data connection and reliable transaction matching. A notice that funds reached a bank account does not move those funds into PayPal, establish escrow or authorize another transfer. Bank-held conditional funds are a proposed partner capability, not verified Zelle functionality.

## Scope and how it scales

Sandbox and synthetic data only. No live money, production secrets, private messages or partner-access claims. This document records the concept; it does not add working code or prove an integration.

For a live version, validate partner access and the pooling/custody model with PayPal and any bank partner, including licensing and compliance requirements; none of that is required to show a clearly labeled hackathon simulation.

## Public sources

1. PayPal, authorize and capture: https://developer.paypal.com/docs/checkout/standard/customize/authorization/
2. PayPal, Venmo checkout: https://developer.paypal.com/venmo
3. PayPal, Venmo payouts: https://developer.paypal.com/payouts/venmo
4. PayPal, Payouts API integration: https://developer.paypal.com/docs/payouts/standard/integrate-api/
5. PayPal, Venmo sandbox support and limits (updated September 14, 2026): https://developer.paypal.com/venmo/test
6. Cash App Pay, partnerships: https://developers.cash.app/cash-app-pay-partner-api/guides/partnerships/partner-with-cash-app-pay
7. Cash App Pay, API quickstart: https://developers.cash.app/cash-app-pay-partner-api/guides/technical-guides/integrating-with-cash-app-pay/api-integration-quickstart
8. Cash App Pay, payouts: https://developers.cash.app/cash-app-pay-partner-api/guides/technical-guides/payouts/about
9. Zelle, network partners: https://www.zelle.com/join-zelle-network/partners
10. J.P. Morgan, Zelle disbursements: https://developer.payments.jpmorgan.com/docs/treasury/global-payments/capabilities/global-payments/zelle-disbursements
11. U.S. Bank, disbursements via Zelle: https://developer.usbank.com/products/disbursements-via-zelle/v1
