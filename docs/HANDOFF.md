# Handoff notes

Submission deadline: Thu Nov 12, 2026, 12:00 pm Pacific (2 pm CT), per https://paypalaihackathon.devpost.com/rules.

## Live demo (Render, free plan, real PayPal sandbox)
- Service haggle-court, https://haggle-court.onrender.com. Runs in sandbox mode since Oct 18, 2026. Auto-deploy does not trigger, so deploy manually (Dashboard, Manual Deploy, Deploy latest commit) after every push.
- AI role: Gemini on Vertex AI writes bot banter and suggests judge weights. Code computes all money. Any error or cap falls back to scripted lines.
- Render env vars: GOOGLE_SA_JSON (service account key, from the owner's vault, never in the repo), HAGGLE_MAX_LLM_CALLS=150, and since Oct 18, 2026 PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET (owner's sandbox app, approved by the owner Oct 17). Per-day cap is 300 (default). Render Shell is not available on the free plan.
- Authorization: the owner approved using Google credits on Oct 7, 2026. That covers credits only, not card billing.

## Key removal (planned Oct 26, 2026)
Google credits expire around Oct 27 and the Cloud account is paid. Before then:
1. Delete GOOGLE_SA_JSON (and HAGGLE_MAX_LLM_CALLS) in Render, Environment, then deploy. The demo reverts to scripted banter.
2. Revert the AI wording in README.md, docs/DEVPOST.md, and the banner in src/haggle/web/index.html to say banter is scripted unless a key is configured.
3. Keep the owner informed. Keep the key only if the owner says so.

## Submission checklist (from the rules)
1. Video length must be under 3 minutes. Current cut: rehearsal-live-ai-v2.mp4, about 149 s. Re-check length after any edit.
2. Project must stay testable through Dec 15, 2026, but the key is removed Oct 26. The video shows live AI. Truthful route, no extra spend by default:
   - Devpost text and video caption say the video was recorded Oct 7 with live Gemini, and the public demo falls back to scripted lines when no key is configured.
   - README has "Try the live AI role yourself": judges run locally with their own key. No public secrets.
   - Optional, needs the owner's approval: a funded key kept on Render through Dec 15 (cost about $0.002 per live run by estimate, capped 300 runs per day). Do not restore without approval.

## Buyer-wallet approval path (built Oct 14, 2026)
- Code: src/haggle/wallet.py, paypal.create_approval_order, /api/wallet/start, /wallet/return, /wallet/cancel, "Approve as buyer" button. Tests: tests/test_wallet.py (local fake PayPal server). 38 tests pass.
- Verified locally with screenshots of the return page (capture and void paths) in mock mode. Sandbox client keys are on Render since Oct 18, 2026 (owner approved Oct 17). Not yet verified: real PayPal sandbox buyer approval (needs a Personal sandbox buyer login) and live webhook delivery.
- UPDATE Oct 15 5:53pm CDT: status.render.com showed Builds and Deploys Operational, one manual deploy succeeded, the wallet path and "Approve as buyer" button are live on https://haggle-court.onrender.com (mock mode, Simulated step wording verified in the browser). Earlier history: manual deploy returned "Deploy Error: Service Unavailable" on Oct 14 4:43-4:44pm CDT while https://status.render.com showed Builds and Deploys degraded (fix being monitored since 19:45 UTC). That Oct 14 attempt failed and the later Oct 15 deploy superseded it. Real PayPal sandbox buyer approval and live webhook delivery remain unverified.

## Remaining work to submission (status Oct 17, 2026)

### Oct 18, 2026 update: hosted sandbox verified
- Hosted /healthz: {"status":"ok","mode":"sandbox","ai":"vertex","ai_last_error":null}.
- Happy path verified against the real sandbox from the hosted service: order 29T06258011215243, authorization 29N71203PS0575744, capture 2RB244176C242244M, payout batch 5BW7SBCJQFV2N. Void path verified: order 3GA79741HJ473604F, voided authorization 98W397609T970273V.
- Browser UI run verified visually: order 5J6904065N2185037, capture 8ST53730C8690012E, payout batch TS879E7LHHCV4, shares 67.20 / 33.60 x3.
- 38 tests pass on a fresh clone. Git history scan across all 92 commits found no matches for the private-key and secret patterns checked.
- Devpost draft (submission id 1245184, not submitted) filled and saved Oct 18: title, tagline, full description, tags, demo and repo links, and the additional-info answers. Saved additional-info answers are visible to hackathon judges and organizers. Those answers (Individual, United States, New project, sponsor Render, and the N/A fields) were agent-inferred from memory and repo history and saved without the owner's explicit approval of the values; owner review and correction are required before submission. Still empty: the required demonstration video URL.
- Still unverified: real sandbox buyer approval (needs a Personal sandbox buyer login) and live webhook delivery (needs PAYPAL_WEBHOOK_ID; registration script needs the sandbox creds locally or the owner runs it in the developer console).
Not submission-ready today. Three buckets:
1. Scheduled cleanup (agent, no owner input needed): the Oct 26 key removal above, plus a final check around Nov 5 (fresh-clone tests, end-to-end demo pass, DEVPOST text refresh, video link). About 1-2 hours total.
2. Hosted real-sandbox verification: the server rails and UI now run against the real sandbox on the hosted service (verified Oct 18, see the update above). Remaining in this bucket: run the buyer approval end to end (needs a Personal sandbox buyer login) and register and verify the live webhook (needs the sandbox creds locally or console access). scripts/register_webhook.py is ready for that: run it with PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in the environment, then set the printed PAYPAL_WEBHOOK_ID on Render and redeploy.
3. Owner access/approval gates: the Devpost sign-in identity, the hosted sandbox credentials decision, and the owner's final review of the video and entry before upload and submission. Emailing the video is an optional delivery choice, not a blocker.

Rules risk: the hosted demo now runs the real sandbox end to end (verified Oct 18), so the integration requirement is covered. Remaining gaps before claiming full readiness: the buyer approval flow has only run against a local fake, and live webhook delivery is unverified. Do not claim full readiness until those pass.

Video accuracy: the 149 s cut records the mock (Simulated) flow. The hosted demo now runs the real sandbox, so the video package needs an accuracy review before submission.
