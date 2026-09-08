# Memory Director — Project Brief

## The problem

The project began with its creator helping her mum make short videos every
Saturday. The goal is to let older adults create those films independently,
without learning a complicated editor.

Older adults often have many meaningful phone photos and videos but need help to turn them into a short piece worth sharing. Common editing applications have dense interfaces and ask users to make too many technical choices: which clips to keep, what a foreign location was called, which music suits an occasion, and how to write a caption.

## The product

Memory Director is a mobile-first web application that guides a user through:

1. Deliberately select 1–15 consented photos and videos from the device picker.
2. Describe a memory by voice or text and arrange the selected media.
3. Choose an original memory song, gentle instrumental music, or no music.
4. Press **Make my film** and receive a vertical 60-second preview on the same page.
5. Choose **Save video** or **Share video**. Sharing uses the device-native sheet when supported and otherwise explains how to save first.

## Audience

- Primary: older adults making short travel or family memory films.
- Supporting: family members who help confirm unfamiliar places, names, or music choices.

## Differentiator

The core experience combines a simple voice/text request with selected media,
a validated production plan, and a playable film the user controls. The official
`mcp-clickhouse` consent/export path can block rendering and export when required
consent evidence is missing.

A separate deployed Agent Engine planner demonstrates an approved, read-only
ClickHouse preference lookup. It is not connected to the public web interface.
The current web flow uses seeded demonstration preferences and does not retain a
person's accepted or rejected creative choices for future projects.

## MVP boundary

The MVP focuses on a 60-second vertical travel, family, or everyday-life film, large high-contrast captions, Mandarin or English requests, and device-controlled sharing. It does not publish to social platforms, browse an entire phone library, use commercial songs without rights, or make unconfirmed claims about people or locations. The user can choose an original AI memory song, gentle instrumental, or no music; unavailable or unsafe music requests fall back safely.

## Current delivery status

The repository and public deployment include the one-page production UI, browser
voice fallback, mixed-media selection and ordering, explicit consent, three
soundtrack choices, direct Gemini storyboard planning, the ClickHouse MCP
consent/export path, deterministic 60-second rendering, inline preview, Make
again, Save, and native-share support with a fallback. A separate Agent Engine
production-proposal endpoint and its approved ClickHouse preference tool are
deployed and workflow-smoke verified, but the public Web UI does not call that
endpoint. Desktop and mobile-emulated journeys have verified original-song and
no-music rendering. ST-52 additionally records an all-pass iPhone 11 journey for
voice, touch reorder, phone-video preview, saved-file behavior, native Share, and
instrumental audio. Android and native screen-reader coverage remain unclaimed.
ST-9 records the approved, rights-reviewed fixtures and generated song; the final
three-minute submission recording remains in ST-17. See the
[capability evidence matrix](CAPABILITY_EVIDENCE.md) for exact claim status.

## Success criteria for the demo

- A voice/text request and deliberately selected media become an understandable preview.
- The selected media order remains visible and reversible; originals are never deleted.
- An uncertain location is omitted or confirmed before final copy uses it.
- Sanitized runtime evidence proves the official ClickHouse MCP consent/export decision without exposing credentials or presenting a tool log as an in-app screen.
- No render or export continues when that gate denies the request.
- The user receives an MP4 to save and share manually.

## Operating the public demo

GitHub Actions and Terraform provide guarded deployment workflows across Google
Cloud infrastructure and services, public-domain configuration, ClickHouse schema
and access setup on an existing Cloud service, and Agent Engine deployment with
runtime verification. Four layers of cost control combine application quotas,
edge and compute limits, billing safeguards, and media retention. Billing alerts
and spend caps are not instantaneous.

See [architecture and deployment details](ARCHITECTURE.md), the
[cost-control runbook](operations/USAGE_COST_CONTROLS.md), and the current
[submission story](submission/DEVPOST_PROJECT_PAGE.md).
