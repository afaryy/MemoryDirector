# Memory Director

Memory Director is a voice-led memory-film producer for older adults. It helps a user turn deliberately selected, consented photos and videos into a 60-second vertical memory film for device-controlled saving and sharing. The current public product is [memorydirector.com](https://memorydirector.com/).

## Product safeguards

- Google Cloud AI is the only AI provider used by the product.
- The ClickHouse track requires a runtime query through the official `mcp-clickhouse` server.
- The MVP never publishes to social networks on a user's behalf.
- Media choices are reversible, uncertain facts require confirmation, and a consent/export gate must pass before the film is saved.
- The browser sees only files the user deliberately selects; it does not scan a phone library or post directly to social networks.

## Local development

```bash
cd services/api
uv run pytest -v
uv run uvicorn app.main:app --reload --port 8000

cd ../../apps/web
npm install
npm run test -- --run
npm run dev
```

The web app calls `http://localhost:8000` by default. For a deployed web client, set
`NEXT_PUBLIC_API_BASE_URL` in `apps/web` and set `WEB_ORIGINS` in `services/api` to the
comma-separated, exact browser origins allowed to call the API.

## Repository documents

- [About the product](docs/ABOUT.md)
- [Project brief](docs/PROJECT_BRIEF.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Current capability evidence](docs/CAPABILITY_EVIDENCE.md)
- [Mobile production flow](docs/ux/MOBILE_PRODUCTION_FLOW.md)
- [Demo media rights register](docs/demo/MEDIA_RIGHTS_REGISTER.md)
- [Three-minute demo runbook](docs/demo/DEMO_RUNBOOK.md)
- [English prompting pack](docs/prompts/memory-director-prompts.md)
- [Terraform bootstrap and state lifecycle](docs/operations/TERRAFORM_BOOTSTRAP.md)
- [Application deployment](docs/operations/APP_DEPLOYMENT.md)
- [Public-domain operations](docs/operations/public-edge.md)
- [Devpost project page](docs/submission/DEVPOST_PROJECT_PAGE.md)
- [ST-32 competition compliance checklist](docs/submission/SUBMISSION_CHECKLIST.md)
- [ST-33 public evidence package](docs/submission/EVIDENCE_PACKAGE.md)
- [Three-minute demo script](docs/submission/DEMO_SCRIPT.md)

Internal planning artifacts are kept separate from the public product-documentation path.

## Licence

MIT. See [LICENSE](LICENSE).
