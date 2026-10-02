# Haggle Court

**Pitch:** Agents negotiate the price, then settle the bill. Paste a product link for something a group is buying. A buyer agent haggles live against a seller agent (coupons, bundle asks, price match). Once the deal lands, a judge agent reads the receipt and the group chat, rules who owes what with a short verdict, and sends PayPal sandbox payment requests to each person.

## Demo story (under 3 min)

1. 0:00 - Paste a $120 product link. Type "four of us, buying together."
2. 0:20 - Split screen: buyer agent vs seller agent, trading offers. Price ticks $120 to $94. Show the "saved $26" counter.
3. 1:15 - Deal lands. A sandbox order fires through PayPal.
4. 1:30 - Drop in a 20-message group chat argument ("I only had one slice"). The judge agent rules on shares and reads a short verdict aloud.
5. 2:15 - Four PayPal sandbox payment requests go out. One participant pays in the sandbox and the ledger updates.
6. 2:45 - Close on the numbers: saved $26, split settled, zero manual math.

## Agent personas

The buyer and seller agents are written in the style of cranky old hecklers, Statler and Waldorf style, no balcony required. Their yelling at each other is the demo centerpiece. This is a style note only: the project does not use or claim any of those characters.

## Build outline (sandbox, about 6 weeks)

- Week 1: repo shell, one agent chat UI with two panes, PayPal sandbox app and credentials.
- Weeks 2-3: Buyer agent using the PayPal Agent Toolkit MCP tools. Seller agent is a scripted LLM persona with a price floor and a few concessions.
- Week 4: Sandbox order creation when the deal lands.
- Week 5: Judge agent: parse receipt text/image, read chat, output shares plus verdict. Create sandbox invoices or payment requests per person.
- Week 6: Ledger view, polish, 3-minute demo script, public README.

## Fit for agentic commerce

Two agents transact with each other, a third agent settles the aftermath, and money moves only after an agreed outcome. It sits on the buyer and group-payment side. PayPal's published Agent Toolkit, Agent Ready and Store Sync cover merchant plumbing and single-agent use (developer.paypal.com/ai-tools/toolkit, developer.paypal.com/agent-ready/overview).

## Notes

Public sources only. Sandbox payments only, no real funds. Hackathon rules (paypalaihackathon.devpost.com/rules, Section 4) allow multiple submissions if each is substantially different, so this combined entry would use up the Haggle Bot and Split Court ideas as one.
