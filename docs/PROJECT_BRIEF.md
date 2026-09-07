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

The product does not only generate a one-off edit. It keeps an explainable creative memory of a user's accepted or rejected preferences. During the next project, the agent queries ClickHouse through the official `mcp-clickhouse` server and can explain recommendations such as: “You chose gentle festive instrumentals twice and rejected loud pop, so I placed gentle instrumental music first.”

## MVP boundary

The MVP focuses on a 60-second vertical travel, family, or everyday-life film, large high-contrast captions, Mandarin or English requests, and device-controlled sharing. It does not publish to social platforms, browse an entire phone library, use commercial songs without rights, or make unconfirmed claims about people or locations. The user can choose an original AI memory song, gentle instrumental, or no music; unavailable or unsafe music requests fall back safely.

## Current delivery status

The repository and public deployment include the one-page production UI, browser voice fallback, mixed-media selection and ordering, explicit consent, three soundtrack choices, an Agent Engine planner, the official ClickHouse MCP preference and consent/export paths, deterministic 60-second rendering, inline preview, Make again, Save, and native-share support with a fallback. Desktop and mobile-emulated production journeys have verified original-song and no-music rendering. Physical-device voice, touch, saved-file, native-share, and instrumental evidence remains in ST-52; rights-cleared media and the final three-minute submission recording remain in ST-9 and ST-17. See the [capability evidence matrix](CAPABILITY_EVIDENCE.md) for exact claim status.

## Success criteria for the demo

- A voice/text request and deliberately selected media become an understandable preview.
- The system explains selected or held-back media without deleting originals.
- An uncertain location is omitted or confirmed before final copy uses it.
- The official ClickHouse MCP path visibly checks the consent/export decision.
- No render or export continues when that gate denies the request.
- The user receives an MP4 to save and share manually.
