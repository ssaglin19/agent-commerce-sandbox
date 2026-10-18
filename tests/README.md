# tests

Unit tests, 38 total, all runnable offline. Run from the repo root:

    PYTHONPATH=src python3 -m unittest discover -s tests

They use the mock PayPal client and a local fake PayPal server
(`tests/test_wallet.py`), never the real sandbox, so no credentials are needed.
The real-sandbox smoke check is separate: `src/haggle/sandbox_check.py`, which needs
`PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` in the environment (never committed).
