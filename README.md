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

cd ../../apps/web
npm install
npm run test -- --run
```

## Repository documents

- `docs/superpowers/specs/2026-08-16-memory-director-design.md` — product architecture and submission evidence.
- `docs/superpowers/plans/2026-08-16-memory-director-mvp.md` — implementation sequence.
- `docs/prompts/memory-director-prompts.md` — versioned English production prompts.
- `docs/research/agentic-cinema-link-archive.md` — challenge links and compliance notes.

## Licence

MIT. See [LICENSE](LICENSE).
