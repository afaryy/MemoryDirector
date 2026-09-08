# About Memory Director

Memory Director is a mobile-first, voice-led memory-film producer for older adults.

A user chooses a small group of family or travel photos and videos, says what they would like to remember, arranges the selected media, chooses an original memory song, gentle instrumental, or no music, and lets Memory Director prepare a 60-second vertical preview. The finished preview has separate **Save video** and **Share video** actions, so the user remains in control of where it goes.

## Inspiration

Every Saturday, I help my mum make short videos. The editing tools available to
her are too complicated, so making a video has become something she needs my help
with each week.

That experience inspired Memory Director: a simple app that lets my mum and other
older adults describe a memory through voice or text, choose their photos and
clips, and create a short film themselves. The goal is independent storytelling,
with the user deciding what to make, save, and share.

## Why it matters

Most video editors expect people to understand a timeline, trimming, music licensing, captions, and publishing controls at once. That is unnecessarily difficult when the goal is simply to share a meaningful moment. Memory Director turns that work into a calm sequence of one decision at a time.

## Principles

- **Voice first, text always available.** Browser voice input is optional; typing remains a reliable fallback.
- **Consent before processing.** The user confirms they have permission to use selected media before generation starts.
- **Nothing is silently deleted or published.** Selections are reversible and the user posts to WeChat, Douyin, or another platform themselves.
- **Facts need confidence.** Uncertain locations, people, and dates are not placed in final copy without confirmation.
- **The user controls saving and sharing.** A consent/export gate must pass before rendering. Saving downloads the MP4; sharing uses the native share sheet when supported and otherwise gives save-first guidance.

## How it works

The Next.js / React web interface calls FastAPI on Cloud Run. Gemini on Vertex AI
provides a constrained storyboard, the API validates it, and FFmpeg renders a
60-second portrait MP4. Google Lyria supports the original music option with
fallbacks. Private Cloud Storage holds consented media.

The official `mcp-clickhouse` integration checks selected-media consent evidence
before rendering and again before export. ClickHouse holds anonymised workflow
events and seeded demonstration preferences, not raw photos or videos. The public
web flow does not maintain durable per-user creative preferences.

A separate Google ADK / Vertex AI Agent Engine production-planning endpoint uses
an approved, read-only ClickHouse preference tool and has passed hosted smoke
checks. The current public web interface uses the direct Gemini storyboard path;
connecting it to Agent Engine is future work.

## Keeping the service affordable and repeatable

GitHub Actions and Terraform automate Google Cloud infrastructure, containerized
services, public-domain configuration, ClickHouse schema and access setup, and
Agent Engine deployment with runtime verification. ClickHouse setup uses an
existing Cloud service. Workload Identity Federation supports deployment
authentication, and Secret Manager holds runtime credentials.

Four layers limit unnecessary cost: Firestore-backed usage quotas before costly
work, Cloud Armor rate limits and bounded Cloud Run scaling, billing alerts and
configured service-specific spend caps, and private-media lifecycle deletion.
Billing enforcement and deletion are asynchronous; these controls do not guarantee
an instantaneous spending ceiling. See the [architecture](ARCHITECTURE.md) and
[cost-control runbook](operations/USAGE_COST_CONTROLS.md) for details.

## What is verified, and what comes next

Desktop and mobile-emulated journeys verified original-song and no-music films.
A physical iPhone 11 journey verified voice input, touch reordering, video preview,
instrumental audio, saving, and native sharing.

Next steps are connecting the separate Agent Engine path to the public interface,
expanding Android and assistive-technology testing, and exploring consent-based
creative preferences. These remain future work, not claims of current coverage.

The current implementation, deployment, physical-device, and final-submission evidence are tracked separately in the [capability evidence matrix](CAPABILITY_EVIDENCE.md).
