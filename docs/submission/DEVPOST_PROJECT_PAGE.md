# Memory Director

## One-line pitch

Memory Director turns a phone album into a short, shareable memory film through
one calm, voice-led decision at a time.

## The problem

Older adults often have meaningful photos and videos but still need help with
the work around them: deciding what to keep, remembering an unfamiliar place,
choosing a suitable music feeling, writing a caption, and trimming a clip.
Traditional editors expose a dense timeline and too many technical choices at
once. A family member becomes the editor by default.

## What we built

Memory Director is a mobile-first web app and Google Cloud API. A user can speak
or type a request, select photos and videos, confirm permission to use them,
review an explainable plan, and approve a deterministic vertical export. The
result is an MP4, cover image, title, and caption that the user saves and posts
manually to the platform of their choice.

The agent is deliberately bounded:

- voice is optional; typed input is always available;
- consent is required before media processing;
- uncertain place claims require confirmation;
- privacy flags remain visible for review;
- held-back media is not silently deleted;
- rendering is blocked until the user approves the plan;
- no social account or automatic publishing permission is requested.

## Why it is agentic

The system coordinates several evidence-based decisions instead of applying a
single opaque filter:

1. Gemini turns a plain-language memory request into a concise production plan.
2. Multimodal Gemini analysis describes only observable media properties and
   returns allow-listed privacy signals.
3. The production flow asks for confirmation when a place or fact is uncertain.
4. The official `mcp-clickhouse` server recalls anonymised creative preferences
   and render history so a recommendation can explain why a warm, cheerful, or
   festive direction was suggested.
5. The user approves the plan before the deterministic renderer creates the
   final package.

## Technology

- Next.js and React mobile-first web interface with browser voice fallback.
- FastAPI on Cloud Run for validation, consent, private media boundaries,
  storyboard requests, and export.
- Google Cloud Vertex AI Gemini for production planning and media analysis.
- Private Google Cloud Storage for consented originals.
- ClickHouse Cloud through the official `mcp-clickhouse` integration for
  explainable preference recall.
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
the API returned health 200, the web page returned 200, and `/renders/export`
returned a valid ZIP containing an MP4, JPG cover, and TXT caption. The final
submission recording must use only assets approved in the rights register.

## What we would do next

The next product step is to connect the same consented flow to a larger,
rights-registered family album and add a user-visible review card for each
privacy flag. The core safety boundary remains the same: Memory Director
directs the memory, but the user decides what leaves the phone.

## Repository and licence

- Source: https://github.com/afaryy/MemoryDirector
- Licence: MIT ([`LICENSE`](../../LICENSE))
