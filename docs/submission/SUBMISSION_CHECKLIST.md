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

The current `ProductionWizard` calls `/media/analyze`, `/storyboards`, media
decision endpoints, `/renders`, and `/renders/export`. The API now calls the
authenticated ClickHouse MCP runtime when `CLICKHOUSE_MCP_ENDPOINT` and the
Secret Manager credential payload are configured. Keep the hosted evidence
unchecked until the visible flow and recording prove the cloud wiring:

- [x] Wire media analysis and privacy-flag review into the Web flow.
- [x] Wire the authenticated ClickHouse MCP preference query into the visible
      recommendation step in the API/Web contract.
- [x] Wire the approved export package into the Web flow.
- [ ] Wire place confirmation into the visible recommendation step.
- [ ] Verify the hosted ClickHouse endpoint, recommendation, and export in the
      final recording.

## Human release gates

- [ ] Complete 15–25 rows in [`MEDIA_RIGHTS_REGISTER.md`](../demo/MEDIA_RIGHTS_REGISTER.md).
- [ ] Confirm every photo, video, voice, and music item is team-owned, synthetic,
      public-domain, or covered by recorded permission.
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
- **Tagline:** A voice-led producer for shareable family and travel memories.
- **Built with:** Google Cloud, Vertex AI Gemini, Cloud Run, Cloud Storage,
  Terraform, ClickHouse Cloud, official `mcp-clickhouse`.
- **Source code:** https://github.com/afaryy/MemoryDirector
- **Hosted app:** https://memory-director-sandbox-web-c3dzm7e76a-ts.a.run.app/
- **Demo video:** `VIDEO_URL_TO_BE_ADDED_AFTER_RECORDING`
- **Licence:** MIT
