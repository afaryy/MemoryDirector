# Memory Director

## One-line pitch

Memory Director turns deliberately selected phone moments into a short,
shareable memory film through one calm, voice-led action.

## The problem

Older adults often have meaningful photos and videos but still need help with
the work around them: deciding what to keep, remembering an unfamiliar place,
choosing a suitable music feeling, writing a caption, and trimming a clip.
Traditional editors expose a dense timeline and too many technical choices at
once. A family member becomes the editor by default.

## What we built

Memory Director is a mobile-first web app and Google Cloud API. The target
journey is deliberately simple: the person speaks or types a request, chooses
their own photos and videos through the device picker, presses **Make my
film**, watches a portrait preview, then chooses **Save & share**. The
submission recording will show only capabilities that are working through this
visible flow; a synthetic API fixture export is not presented as a complete
hosted-UI journey.

The agent is deliberately bounded:

- voice is optional; typed input is always available;
- consent is required before media processing;
- uncertain place claims require confirmation;
- privacy flags remain visible for review;
- held-back media is not silently deleted;
- the browser sees only files the user deliberately selects;
- the ClickHouse MCP consent/export gate can block rendering and export;
- no social account or automatic publishing permission is requested.

## Why it is agentic

The intended production flow coordinates several evidence-based decisions
instead of applying a single opaque filter:

1. Gemini turns a plain-language memory request into a constrained production brief.
2. Multimodal Gemini analysis describes only observable media properties and
   returns allow-listed privacy signals.
3. The production flow omits an uncertain place or fact until the user confirms it.
4. The official `mcp-clickhouse` server is the runtime integration for
   anonymised preferences and the required consent/export decision.
5. A deterministic renderer makes the approximately-one-minute portrait film
   from a constrained storyboard; the model never directly encodes video.

The repository contains early adapter, schema, consent/privacy, and export
foundations. The simplified UI, visible automatic film, ClickHouse export gate,
and final recorded proof remain release gates in the checklist.

## Technology

- Next.js and React mobile-first web interface with browser voice fallback.
- FastAPI on Cloud Run for validation, consent, private media boundaries,
  storyboard requests, and export.
- Google Cloud Vertex AI Gemini for production planning and media analysis.
- Private Google Cloud Storage for consented originals.
- ClickHouse Cloud through the official `mcp-clickhouse` integration for the
  explainable preference and consent/export path (hosted runtime proof pending).
- Google Lyria for the original memory-song feature only after ST-38 implements
  and verifies its safety/provenance boundary.
- Terraform modules and GitHub Actions with OIDC/WIF for repeatable sandbox
  infrastructure and deployments.

## Proof of a working deployment

- Hosted web app:
  https://memory-director-sandbox-web-c3dzm7e76a-ts.a.run.app/
- Hosted API health endpoint:
  https://memory-director-sandbox-api-c3dzm7e76a-ts.a.run.app/health
- Deployment workflow:
  https://github.com/afaryy/MemoryDirector/actions/runs/32362975036
- Architecture and data boundaries: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md)
- Three-minute recording plan: [`docs/demo/DEMO_RUNBOOK.md`](../demo/DEMO_RUNBOOK.md)
- Rights gate: [`docs/demo/MEDIA_RIGHTS_REGISTER.md`](../demo/MEDIA_RIGHTS_REGISTER.md)

The hosted sandbox has been smoke-tested with a non-sensitive synthetic image:
the API returned health 200, the web page returned 200, and a direct API call
to `/renders/export` returned a valid ZIP containing an MP4, JPG cover, and TXT
caption. This is API evidence, not a claim that the current Web page already
drives that endpoint. The final submission recording must use only assets
approved in the rights register and must update this distinction after UI
wiring is complete.

## What we would do next

The next product step is to implement the simplified mobile flow, deterministic
approximately-one-minute preview, original memory song with a safe fallback,
and ClickHouse MCP consent/export gate. The core safety boundary remains the
same: Memory Director directs the memory, but the user decides what leaves the
phone.

## Repository and licence

- Source: https://github.com/afaryy/MemoryDirector
- Licence: MIT ([`LICENSE`](../../LICENSE))
