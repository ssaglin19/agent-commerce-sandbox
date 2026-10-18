# src

Two modules run by the same server:

- `haggle/` - Haggle Court: two bots negotiate a group-buy price, a judge splits the
  cost, and PayPal holds then settles the money. Key files: `flow.py` (end-to-end
  session), `negotiation.py` (bot loop), `judge.py` (split ruling), `paypal.py`
  (sandbox client plus a mock with the same interface), `wallet.py` (buyer approval
  path), `webhook.py` (signed event log), `server.py` (HTTP server and one-page UI).
- `pool/` - group-purchase coordinator: collects participant approvals, funds the
  merchant order and rolls back on failure. Key files: `coordinator.py`, `rails.py`,
  `session.py`.

Money is computed by code only. The optional AI role (Gemini on Vertex AI) writes
bot banter and suggests judge weights; any error or cap falls back to scripted lines.
