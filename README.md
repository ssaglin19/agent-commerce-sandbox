# Haggle Court (PayPal AI hackathon entry)

Two crotchety bots (Statler = buyer, Waldorf = seller) haggle a group buy down. The agreed price creates a
PayPal sandbox order with intent AUTHORIZE (funds held). A judge bot reads the receipt and the group chat
argument and rules who owes what. The order is captured and split payments go out.

## Run
```
python3 -m unittest discover tests
PYTHONPATH=src python3 -m haggle.server   # open http://localhost:8000
```
No keys needed: without PayPal credentials it runs in mock mode (same interface).
Sandbox: set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` (developer.paypal.com sandbox app; see `.env.example`).
Optional: `ANTHROPIC_API_KEY` makes the bots and judge use an LLM; otherwise scripted lines.

## Layout
`src/haggle/` negotiation, judge, paypal client (Orders v2 authorize/capture, Payments v2 void, Payouts), flow, web server + page.
Never commit keys. MIT licensed.
