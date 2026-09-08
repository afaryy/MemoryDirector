# Memory Director — Project Brief

## The problem

Older adults often have many meaningful phone photos and videos but need help to turn them into a short piece worth sharing. Common editing applications have dense interfaces and ask users to make too many technical choices: which clips to keep, what a foreign location was called, which music suits an occasion, and how to write a caption.

## The product

Memory Director is a mobile-first web application that guides a user through:

1. Describe a memory by voice or text.
2. Deliberately select 1–15 consented photos and videos from the device picker.
3. Press **Make my film**.
4. Receive an automatically edited, vertical 60-second preview on the same page.
5. Choose **Save video** or **Share video**. Sharing uses the device-native sheet when supported and otherwise explains how to save first.

## Audience

- Primary: older adults making short travel or family memory films.
- Supporting: family members who help confirm unfamiliar places, names, or music choices.

## Differentiator

The official `mcp-clickhouse` path demonstrates how a bounded planner can read a
seeded, approved preference and explain its music recommendation. The current
public Web flow uses a shared demonstration partition and does not write a person's
accepted or rejected choices for future projects; durable per-user creative memory
is not a submitted capability.

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
