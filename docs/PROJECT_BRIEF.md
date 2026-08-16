# Memory Director — Project Brief

## The problem

Older adults often have many meaningful phone photos and videos but need help to turn them into a short piece worth sharing. Common editing applications have dense interfaces and ask users to make too many technical choices: which clips to keep, what a foreign location was called, which music suits an occasion, and how to write a caption.

## The product

Memory Director is a mobile-first web application that guides a user through:

1. Describe a memory by voice or text.
2. Select consented photos and videos from the phone.
3. Receive a simple, explainable production plan from Gemini.
4. Confirm uncertain places and choose a music direction.
5. Approve the storyboard before any render is requested.
6. Save the resulting video package and post it manually.

## Audience

- Primary: older adults making short travel or family memory films.
- Supporting: family members who help confirm unfamiliar places, names, or music choices.

## Differentiator

The product does not only generate a one-off edit. It keeps an explainable creative memory of a user's accepted or rejected preferences. During the next project, the agent queries ClickHouse through the official `mcp-clickhouse` server and can explain recommendations such as: “You chose gentle festive instrumentals twice and rejected loud pop, so I placed gentle instrumental music first.”

## MVP boundary

The MVP focuses on a 45–60 second vertical travel or family video, large high-contrast captions, Mandarin or English requests, and manual sharing. It does not publish to social platforms, use commercial songs without rights, or make unconfirmed claims about people or locations.

## Current delivery status

The repository currently includes the mobile production flow, browser voice fallback, consent enforcement, Gemini storyboard request boundary, ClickHouse preference-query adapter, and explicit render-approval API. Real asset upload, multimodal analysis, Cloud-hosted ClickHouse verification, and deterministic MP4 export remain in progress.

## Success criteria for the demo

- A voice/text request becomes an understandable production plan.
- The user sees why media is selected or held back.
- An uncertain location is confirmed before final copy uses it.
- A ClickHouse MCP query visibly informs a preference recommendation.
- No render starts without explicit approval.
- The user receives a video, cover, and caption to save and share manually.
