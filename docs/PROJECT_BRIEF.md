# Memory Director — Project Brief

## The problem

Older adults often have many meaningful phone photos and videos but need help to turn them into a short piece worth sharing. Common editing applications have dense interfaces and ask users to make too many technical choices: which clips to keep, what a foreign location was called, which music suits an occasion, and how to write a caption.

## The product

Memory Director is a mobile-first web application that guides a user through:

1. Describe a memory by voice or text.
2. Deliberately select 1–15 consented photos and videos from the device picker.
3. Press **Make my film**.
4. Receive an automatically edited, vertical preview of approximately one minute.
5. Confirm **Save & share** after the consent/export gate passes, then choose a destination manually.

## Audience

- Primary: older adults making short travel or family memory films.
- Supporting: family members who help confirm unfamiliar places, names, or music choices.

## Differentiator

The product does not only generate a one-off edit. It keeps an explainable creative memory of a user's accepted or rejected preferences. During the next project, the agent queries ClickHouse through the official `mcp-clickhouse` server and can explain recommendations such as: “You chose gentle festive instrumentals twice and rejected loud pop, so I placed gentle instrumental music first.”

## MVP boundary

The MVP focuses on an approximately one-minute vertical travel, family, or everyday-life film, large high-contrast captions, Mandarin or English requests, and manual sharing. It does not publish to social platforms, browse an entire phone library, use commercial songs without rights, or make unconfirmed claims about people or locations. The signature original AI memory-song experience is planned work; until it is verified, generation falls back safely to instrumental or no sound.

## Current delivery status

The repository currently includes browser voice fallback, consent enforcement, Gemini storyboard request boundaries, a ClickHouse preference-query adapter, and export-path foundations. The simplified UI, visible automatic preview, original-song generation, Cloud-hosted ClickHouse consent/export verification, and deterministic MP4 delivery remain in progress.

## Success criteria for the demo

- A voice/text request and deliberately selected media become an understandable preview.
- The system explains selected or held-back media without deleting originals.
- An uncertain location is omitted or confirmed before final copy uses it.
- The official ClickHouse MCP path visibly checks the consent/export decision.
- No render or export continues when that gate denies the request.
- The user receives an MP4 to save and share manually.
