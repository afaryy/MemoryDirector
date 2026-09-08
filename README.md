# Memory Director

Memory Director helps older adults turn their own photos and videos into a
60-second vertical memory film. Describe a memory through voice or text, choose
a soundtrack, and preview a film you can save and share yourself.

[Try the live app](https://memorydirector.com/) ·
[Read the full Project Story](docs/submission/DEVPOST_PROJECT_PAGE.md)

## Inspiration

Every Saturday, I help my mum make short videos. The editing tools available to
her are too complicated, so making a video has become something she needs my help
with each week.

That experience inspired Memory Director. I wanted my mum and other older adults
to create their own short videos by describing what they want and choosing their
photos and clips. The goal is independent storytelling: focus on the memory,
without having to learn a complicated editor.

## How it works

1. **Choose your moments.** Select photos and videos from your device and arrange their order.
2. **Describe your memory.** Type or speak what you want to make; voice availability depends on browser support.
3. **Choose the sound.** Pick an original memory song, gentle instrumental music, or no music.
4. **Make and preview.** Generate a 60-second portrait film and watch it before saving.
5. **Save or share.** Download the MP4 or use the device's native share sheet where supported, with save-first guidance otherwise.

The browser sees only the files you select. Processing requires consent, and
consent evidence is checked before rendering and again before export. Sharing is
a deliberate user action; the app never publishes to social networks on your
behalf. Private Cloud Storage holds consented media, while ClickHouse holds
anonymised workflow events and seeded demonstration preferences, not raw media.

## Architecture at a glance

![Memory Director architecture: selected photos and a voice or text request become a consent-checked, 60-second film for user-controlled saving and sharing.](docs/assets/architecture/memorydirector-architecture.png)

The mobile-first Next.js / React interface calls FastAPI on Cloud Run. Gemini on
Vertex AI supports media analysis and constrained storyboard planning. The API
validates the plan before FFmpeg renders the selected source media, with optional
original music from Google Lyria. Google Cloud AI is the product's only AI provider. The official ClickHouse MCP path checks selected-media
consent evidence before rendering and again before export. The separately deployed
Google ADK / Vertex AI Agent Engine planning endpoint is shown below the main flow
and is labelled **Deployed & smoke-test verified**. Solid arrows show the public
web path; dashed arrows show the separate Agent Engine endpoint. The current web
interface does not call that endpoint.

[Read the architecture guide](docs/ARCHITECTURE.md) for the workflow, module
responsibilities, data boundaries, and verified limitations, or
[download the editable draw.io diagram](docs/assets/architecture/memorydirector-architecture.drawio).

## Automated deployment

We built automated deployment workflows with GitHub Actions and Terraform for Google Cloud infrastructure, containerized services, public-domain configuration, ClickHouse schema and access setup, and ADK Agent Engine deployment with runtime verification.

The workflows build and publish container images, apply infrastructure changes,
configure database access, and verify the Agent Engine tool call before switching
the API to the selected agent. Cloud authentication uses Workload Identity
Federation; runtime credentials are held in Secret Manager.

Deployment workflows can be started manually. Application deployment also supports
a test-success trigger controlled by `AUTO_DEPLOY_ENABLED`; that switch was disabled
in `sandbox` when checked on 8 September 2026. ClickHouse setup targets an existing
Cloud service, and the initial state/WIF bootstrap is separate.

See the [deployment automation details](docs/ARCHITECTURE.md#deployment-automation)
and [workflow definitions](.github/workflows).

## Four-layer cost control

The public demo uses four complementary controls to keep operation affordable:

1. **Application quotas:** Firestore-backed daily usage and concurrency limits before costly work begins.
2. **Edge and compute limits:** Cloud Armor throttling and bounded Cloud Run scaling, with zero minimum instances for the API and web services.
3. **Billing safeguards:** alerts and configured service-specific spend caps, with allowance for enforcement and reporting delays.
4. **Media retention:** private uploads are eligible for lifecycle deletion after one day and exports after three days.

These are layered controls, not a guaranteed instantaneous spending ceiling.
ClickHouse Cloud billing is separate from Google Cloud billing controls. See
[usage and cost controls](docs/operations/USAGE_COST_CONTROLS.md) for the configuration and recorded evidence.

## Verified capabilities and next steps

Desktop and mobile-emulated journeys verified original-song and no-music films.
A physical iPhone 11 journey verified voice input, touch reordering, video preview,
instrumental audio, saving, and native sharing. The separate Agent Engine planning
endpoint and its read-only ClickHouse preference tool passed hosted deployment
smoke checks.

Testing taught us that a useful experience needs fewer decisions, clear feedback,
and a reliable execution layer that turns an AI plan into a playable film. Real
phone testing exposed issues that desktop testing alone could not show.

Next, we plan to connect the Agent Engine planning path to the public interface,
expand testing across Android devices and assistive technologies, and explore
consent-based creative preferences. The current web flow does not yet maintain
durable per-user creative preferences.

See the [capability evidence matrix](docs/CAPABILITY_EVIDENCE.md) for the evidence
behind each claim and [About Memory Director](docs/ABOUT.md) for more context.

## Local development

```bash
cd services/api
uv run pytest -v
uv run uvicorn app.main:app --reload --port 8000

cd ../../apps/web
npm install
npm run test -- --run
npm run dev
```

The web app calls `http://localhost:8000` by default. For a deployed web client, set
`NEXT_PUBLIC_API_BASE_URL` in `apps/web` and set `WEB_ORIGINS` in `services/api` to the
comma-separated, exact browser origins allowed to call the API.

## Repository documents

- [About the product](docs/ABOUT.md)
- [Project brief](docs/PROJECT_BRIEF.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Current capability evidence](docs/CAPABILITY_EVIDENCE.md)
- [Mobile production flow](docs/ux/MOBILE_PRODUCTION_FLOW.md)
- [Demo media rights register](docs/demo/MEDIA_RIGHTS_REGISTER.md)
- [Three-minute demo runbook](docs/demo/DEMO_RUNBOOK.md)
- [English prompting pack](docs/prompts/memory-director-prompts.md)
- [Terraform bootstrap and state lifecycle](docs/operations/TERRAFORM_BOOTSTRAP.md)
- [Application deployment](docs/operations/APP_DEPLOYMENT.md)
- [Public-domain operations](docs/operations/public-edge.md)
- [Devpost project page](docs/submission/DEVPOST_PROJECT_PAGE.md)
- [ST-32 competition compliance checklist](docs/submission/SUBMISSION_CHECKLIST.md)
- [ST-33 public evidence package](docs/submission/EVIDENCE_PACKAGE.md)
- [Three-minute demo script](docs/submission/DEMO_SCRIPT.md)

Internal planning artifacts are kept separate from the public product-documentation path.

## Licence

MIT. See [LICENSE](LICENSE).
