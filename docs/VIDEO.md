# Combined demo video plan (2:50 target, under 3 minutes)

Record Haggle Court and group purchases as one submission. Never show credentials, .env, browser account menus or private project data.

| Time | Screen | Narration |
|---|---|---|
| 0:00-0:12 | Haggle Court title and mode notice | "Group buys die in the group chat. Haggle Court brings the argument and settlement into one project." |
| 0:12-0:38 | Open court, transcript, agreed price | "Statler buys, Waldorf sells. They haggle to a locked price. The current banter is scripted; a model hook is optional." |
| 0:38-1:00 | Authorization, judge, capture | "PayPal sandbox holds the funds. The judge reads the receipt and the group chat, then captures or voids. These are sandbox transactions, not real money." |
| 1:00-1:15 | Group bails out, void result | "When the group backs out, the hold is voided. There is no capture." |
| 1:15-1:48 | Group purchases, haggle checkbox, happy run | "The same negotiated price can feed the group coordinator. Approvals are tied to exact terms. This demo simulates the people approving and the merchant purchase. PayPal shares can use sandbox holds; Venmo is labeled simulated." |
| 1:48-2:05 | Capture and remainder payout batch | "It captures the shares and requests remainder payouts. A batch ID means a request was submitted, not that delivery has been confirmed." |
| 2:05-2:35 | One capture fails, participant table | "If a capture fails, settlement stops. Earlier captures are refunded and remaining holds released. Failed refunds or payouts stay pending rather than being called complete." |
| 2:35-2:50 | Repo and closing title | "One submission: negotiation plus group purchases. Python, PayPal Orders, Payments and Payouts. The MIT code and tests are public." |

## Recording gates
- Dry-run all four scenarios before recording. No automatic retries of settlement requests.
- Mock mode is a valid rehearsal, but label it mock throughout. Do not narrate mock IDs as live sandbox evidence.
- Use a verified sandbox configuration for the final sandbox recording. Public Render remains mock until sandbox keys are approved and installed there.
- Keep the mode notice and SIMULATED labels visible. Participant approvals in the canned demo are not real human authentication.
- Live webhook delivery is not verified yet. Do not claim webhook-driven settlement.
- Upload/publish only after the final video and its audience have been reviewed. No video link exists yet.
