# Agent Commerce Sandbox

Project name and demo scope: TBD.

A starter repository for an AI + PayPal sandbox demo. This is a shell, not a working product. The specific agent-commerce use case will be chosen before implementation.

## Proposed boundaries

- PayPal sandbox only. No live payments or real money.
- An explicit human approval step before any simulated payment.
- No production credentials, personal data, or private conversation content in this repository.
- AI provider, framework, and hosting: TBD.

## Layout

- `src/`: application and AI workflow code
- `payments/`: PayPal sandbox integration
- `tests/`: tests and fixtures using synthetic data
- `docs/`: demo flow and implementation notes
- `.env.example`: empty local configuration template

## Local configuration

Copy `.env.example` to `.env` locally and fill in sandbox credentials. Never commit `.env`. The PayPal client secret must stay server-side, never in browser code.

There are no dependencies or run commands yet. This repository makes no PayPal or AI requests.

## Next discussion

Choose one demo story, define the approval boundary, select the AI and application stack, then build the smallest end-to-end sandbox flow.

## License

MIT. See `LICENSE`.
