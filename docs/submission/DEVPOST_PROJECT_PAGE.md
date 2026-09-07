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

The repository contains the simplified UI, consent and privacy boundaries,
automatic film preview/export path, Agent Engine planner, and ClickHouse MCP
preference and export gates. The approved-media register and final recorded
hosted proof remain release gates in the checklist.

## Technology

- Next.js and React mobile-first web interface with browser voice fallback.
- FastAPI on Cloud Run for validation, consent, private media boundaries,
  storyboard requests, and export.
- Google Cloud Vertex AI Gemini for production planning and media analysis.
- Private Google Cloud Storage for consented originals.
- ClickHouse Cloud through the official `mcp-clickhouse` integration for the
  explainable preference and consent/export path; the hosted Agent Engine smoke
  verifies the preference-tool invocation.
- Google Lyria for an original memory-song option behind prompt-safety,
  provenance, quota, and instrumental/no-sound fallback boundaries.
- Terraform modules and GitHub Actions with OIDC/WIF for repeatable sandbox
  infrastructure and deployments.

## Data sources

- Photos and videos deliberately selected by the user; the app does not scan
  the wider device library.
- The user's typed or spoken production request.
- Anonymised consent, render, and accepted/rejected preference events in
  ClickHouse. ClickHouse stores no raw photos or videos.
- Gemini and Lyria outputs derived from approved request and media context.
- For the public demonstration, only assets approved in the media rights
  register.

## What we learned

- A useful older-adult workflow needs fewer decisions, not a smaller version
  of a professional timeline editor. One request, deliberate media selection,
  one permission gate, preview, and manual save/share proved clearer.
- Agent output becomes production-safe only after deterministic validation.
  The API accepts known media IDs, a closed music choice, and exactly 60
  seconds; it rejects private URIs and malformed plans.
- Partner integration is strongest when it controls a real decision. The
  official ClickHouse MCP tool supplies a bounded preference lookup and consent
  evidence instead of acting as a decorative analytics dashboard.
- Hosted evidence needs stricter wording than local tests. We keep code-level,
  deployed-runtime, and final recorded proof separate in the
  [`ST-33 evidence package`](EVIDENCE_PACKAGE.md).

## Proof of a working deployment

- Hosted web app:
  https://memorydirector.com/
- Hosted API health endpoint:
  https://memorydirector.com/api/health
- Public-edge deployment and HTTPS verification:
  https://github.com/afaryy/MemoryDirector/actions/runs/34118291595
- Agent Engine and ClickHouse preference-tool smoke:
  https://github.com/afaryy/MemoryDirector/actions/runs/34024861486
- Architecture and data boundaries: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md)
- Three-minute recording plan: [`docs/demo/DEMO_RUNBOOK.md`](../demo/DEMO_RUNBOOK.md)
- Rights gate: [`docs/demo/MEDIA_RIGHTS_REGISTER.md`](../demo/MEDIA_RIGHTS_REGISTER.md)

The hosted sandbox has been smoke-tested with non-sensitive synthetic input:
the API returned health 200, the web page returned 200, and the export API
returned a valid ZIP containing an MP4, JPG cover, and TXT caption. The current
Web source drives the consented analysis, Agent Engine planning, export,
preview, download, and share path. The final submission recording must still
prove that complete hosted journey using only assets approved in the rights
register.

## What we would do next

The immediate release step is to approve the demo-media rights register, run
the exact hosted recording journey, and capture the final English-subtitled
video. The core safety boundary remains the same: Memory Director directs the
memory, but the user decides what leaves the phone.

## Repository and licence

- Source: https://github.com/afaryy/MemoryDirector
- Licence: MIT ([`LICENSE`](../../LICENSE))

Video Intelligence is not part of the submitted build and must not be listed
as a technology or claimed in the recording.
