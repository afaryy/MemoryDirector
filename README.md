# Memory Director

Memory Director is a voice-led memory-film producer for older adults. It helps a user turn a consented travel or family album into a 45–60 second vertical video, cover image, title, and caption for manual sharing.

## Hackathon constraints

- Google Cloud AI is the only AI provider used by the product.
- The ClickHouse track requires a runtime query through the official `mcp-clickhouse` server.
- The MVP never publishes to social networks on a user's behalf.
- Media choices are reversible, place claims below 0.85 confidence require confirmation, and render/export requires explicit approval.

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
- [Mobile production flow](docs/ux/MOBILE_PRODUCTION_FLOW.md)
- [Demo media rights register](docs/demo/MEDIA_RIGHTS_REGISTER.md)
- [Three-minute demo runbook](docs/demo/DEMO_RUNBOOK.md)
- [English prompting pack](docs/prompts/memory-director-prompts.md)
- [Hackathon research and compliance links](docs/research/agentic-cinema-link-archive.md)
- [Terraform bootstrap and state lifecycle](docs/operations/TERRAFORM_BOOTSTRAP.md)

Internal planning artifacts are kept separate from the public product-documentation path.

## Licence

MIT. See [LICENSE](LICENSE).
