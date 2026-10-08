# Handoff notes

Submission deadline: Thu Nov 12, 2026, 12:00 pm Pacific (2 pm CT), per https://paypalaihackathon.devpost.com/rules.

## Live demo (Render, free plan, mock PayPal)
- Service haggle-court, https://haggle-court.onrender.com. Auto-deploy does not trigger, so deploy manually (Dashboard, Manual Deploy, Deploy latest commit) after every push.
- AI role: Gemini on Vertex AI writes bot banter and suggests judge weights. Code computes all money. Any error or cap falls back to scripted lines.
- Render env vars: GOOGLE_SA_JSON (service account key, from the owner's vault, never in the repo) and HAGGLE_MAX_LLM_CALLS=150. Per-day cap is 300 (default).
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
