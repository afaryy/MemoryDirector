# Submission checklist

This checklist separates repository evidence from the two items that require a
human release decision: approved demo media and the final recording URL.

## Repository evidence

- [x] Public repository: https://github.com/afaryy/MemoryDirector
- [x] MIT licence: [`LICENSE`](../../LICENSE)
- [x] Product brief: [`docs/PROJECT_BRIEF.md`](../PROJECT_BRIEF.md)
- [x] Architecture and privacy boundaries: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md)
- [x] Mobile interaction acceptance criteria: [`docs/ux/MOBILE_PRODUCTION_FLOW.md`](../ux/MOBILE_PRODUCTION_FLOW.md)
- [x] Terraform and deployment runbook: [`docs/operations/APP_DEPLOYMENT.md`](../operations/APP_DEPLOYMENT.md)
- [x] English prompt pack: [`docs/prompts/memory-director-prompts.md`](../prompts/memory-director-prompts.md)
- [x] ClickHouse MCP proof and schema: [`docs/clickhouse-mcp-proof.md`](../clickhouse-mcp-proof.md)
- [x] Hosted Web URL: https://memory-director-sandbox-web-c3dzm7e76a-ts.a.run.app/
- [x] Hosted API health URL: https://memory-director-sandbox-api-c3dzm7e76a-ts.a.run.app/health
- [x] Latest successful deployment: https://github.com/afaryy/MemoryDirector/actions/runs/32362975036
- [x] Direct synthetic `/renders/export` API smoke evidence is documented; it is
      not represented as a complete hosted Web journey.

## Hosted UI integration gate

The current implementation contains earlier production-flow foundations. Keep
the following evidence unchecked until the simplified visible flow and final
recording prove it:

- [ ] Show the deliberate device-picker selection and removable media cards.
- [ ] Make **Make my film** create a visible approximately-one-minute portrait preview.
- [ ] Wire the authenticated ClickHouse MCP consent/export gate into the visible flow.
- [ ] Wire a real visible MP4 export to **Save & share**.
- [ ] Verify the hosted ClickHouse endpoint, preview, and export in the final recording.
- [ ] If included, prove original AI memory-song generation, safety result, and fallback in the final recording.

## Human release gates

- [ ] Complete 15–25 rows in [`MEDIA_RIGHTS_REGISTER.md`](../demo/MEDIA_RIGHTS_REGISTER.md).
- [ ] Confirm every photo, video, voice, and music item is team-owned, synthetic,
      public-domain, or covered by recorded permission.
- [ ] For every generated song, record model/version, prompt-safety result,
      duration, and available provenance. Do not claim exclusivity or that it
      is copyright-free.
- [ ] Record the actual product flow with English subtitles using only approved
      fixtures: [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).
- [ ] Upload the final three-minute video to the approved public host.
- [ ] Replace this placeholder with the final public video URL:
      `VIDEO_URL_TO_BE_ADDED_AFTER_RECORDING`
- [ ] Open the repository, hosted app, and video in an incognito browser.
- [ ] Confirm the Devpost page contains no credentials, private media, or
      unlicensed music.

## Final Devpost fields

- **Project name:** Memory Director
- **Tagline:** A voice-led producer that turns phone moments into a simple memory film.
- **Built with:** Google Cloud, Vertex AI Gemini, Cloud Run, Cloud Storage,
  Terraform, ClickHouse Cloud, official `mcp-clickhouse`.
- **Source code:** https://github.com/afaryy/MemoryDirector
- **Hosted app:** https://memory-director-sandbox-web-c3dzm7e76a-ts.a.run.app/
- **Demo video:** `VIDEO_URL_TO_BE_ADDED_AFTER_RECORDING`
- **Licence:** MIT
