# Haggle Court demo video (target 2:30, hard cap 3:00)

Screen recording of the web page, voiceover. No music needed.

| Time | Shot | Voiceover |
|---|---|---|
| 0:00-0:15 | Title card: "Haggle Court". Cut to the empty web page. | "Group buys die in the group chat. Everyone argues, nobody pays. So we gave the argument to two bots and the money to PayPal." |
| 0:15-0:35 | Page, Statler and Waldorf names. Click "Run happy path". | "Statler is the buyer. Waldorf is the seller. They haggle the price down while heckling each other." |
| 0:35-1:05 | Chat lines streaming, prices dropping turn by turn. Zoom on the final agreed price. | "Each turn moves the price. When they agree, the price is locked." |
| 1:05-1:30 | Receipt panel: order ID and authorization ID appear. | "The agreed price creates a PayPal order with intent AUTHORIZE. The funds are held, not taken. That is a real sandbox authorization." |
| 1:30-1:55 | Judge verdict panel: "capture", shares per person. | "A judge bot reads the receipt and the group chat. Everyone is in, so it rules capture and works out each person's share." |
| 1:55-2:10 | Capture ID and payout batch ID appear. | "PayPal captures the order and Payouts sends each split. Real IDs, from the live sandbox." |
| 2:10-2:35 | Click "Run void path". Chat shows the group backing out. Verdict: void. No capture ID. | "Now the group chat turns on the deal. The judge reads that half the group is out, rules void, and the authorization is voided. Nobody is charged." |
| 2:35-2:50 | Repo page on GitHub, then end card. | "Orders, Payments and Payouts APIs, two bots, one judge. Code is MIT licensed at github.com/ssaglin19/agent-commerce-sandbox." |

## Recording notes
- Run in the Codespace with sandbox credentials loaded, so the IDs on screen are real.
- Do a dry run first. If the live run is slow, record the two runs separately and cut.
- Do not show the .env file or the PayPal developer dashboard credentials.
- Export 1080p, upload to YouTube or Vimeo as public, paste the link in Devpost.
