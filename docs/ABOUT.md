# About Memory Director

Memory Director is a mobile-first, voice-led memory-film producer for older adults.

A user chooses a small group of family or travel photos and videos, says what they would like to remember, and lets Memory Director prepare a short vertical preview. One concise confirmation then saves the memory film for the user to share manually.

## Why it matters

Most video editors expect people to understand a timeline, trimming, music licensing, captions, and publishing controls at once. That is unnecessarily difficult when the goal is simply to share a meaningful moment. Memory Director turns that work into a calm sequence of one decision at a time.

## Principles

- **Voice first, text always available.** Browser voice input is optional; typing remains a reliable fallback.
- **Consent before processing.** The user confirms they have permission to use selected media before generation starts.
- **Nothing is silently deleted or published.** Selections are reversible and the user posts to WeChat, Douyin, or another platform themselves.
- **Facts need confidence.** Uncertain locations, people, and dates are not placed in final copy without confirmation.
- **The user controls saving.** A consent/export gate must pass before the finished film can be saved or shared.

## ClickHouse integration

Gemini creates constrained production decisions; the official `mcp-clickhouse` integration records and checks consent/export decisions and can recall accepted and rejected preferences so future music or pacing suggestions are explainable.
