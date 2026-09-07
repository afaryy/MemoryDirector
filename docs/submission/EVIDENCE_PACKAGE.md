# ST-33 Devpost evidence package

This index is the claim boundary for the final Memory Director submission. It
maps submission-ready statements to public evidence and keeps unfinished or
unverified technology out of the pitch.

Last audited: **7 September 2026 (AEST)** against the `main` baseline
`506f2fb7249be2fa5a178117f32e8a0b09980fbe`.

## Submission fields

| Field | Submission value | Release status |
| --- | --- | --- |
| Project name | Memory Director | Ready |
| Tagline | A voice-led producer that turns phone moments into a simple memory film. | Ready |
| Partner track | ClickHouse | Must be selected in Devpost |
| Hosted project | <https://memorydirector.com/> | Public and returning HTTP 200 |
| Source repository | <https://github.com/afaryy/MemoryDirector> | Public; MIT licence detected |
| Demo video | `VIDEO_URL_REQUIRED` | Blocked until a public YouTube or Vimeo video is uploaded |
| Written language | English | Ready; final form review required |
| Demo language | English or English-subtitled | Blocked on final video |

Use [`DEVPOST_PROJECT_PAGE.md`](DEVPOST_PROJECT_PAGE.md) as the source for the
long description, [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) for the recording, and
[`SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md) for rules compliance.

## Required runtime evidence

### Gemini and Google Cloud agent runtime

**Submission-safe claim:** Memory Director uses a bounded Google ADK agent on
Vertex AI Agent Engine with Gemini 2.5 Flash to return a schema-validated,
exactly 60-second production plan.

Public evidence:

- [Agent implementation](https://github.com/afaryy/MemoryDirector/blob/main/services/api/app/adk_memory_film_agent.py)
  and [Agent Engine adapter](https://github.com/afaryy/MemoryDirector/blob/main/services/api/app/agent_engine.py).
- [Deployment workflow](https://github.com/afaryy/MemoryDirector/blob/main/.github/workflows/deploy-agent-engine.yml)
  switches the API only after the hosted smoke gate succeeds.
- [Successful hosted Agent Engine run](https://github.com/afaryy/MemoryDirector/actions/runs/34024861486)
  completed the steps “Prove Agent Engine plan and ClickHouse
  preference-tool invocation” and “Switch API only after smoke succeeds.” Its
  sanitized smoke artefact is attached to that run.

Final-demo proof: show a production request producing the visible 60-second
film. Do not expose the Agent Engine resource name if the recording does not
need it.

### Official ClickHouse MCP runtime

**Submission-safe claim:** The agent calls the official `mcp-clickhouse`
server at runtime for a fixed, read-only preference lookup, and export remains
behind a separate consent decision.

Public evidence:

- [Pinned official MCP image](https://github.com/afaryy/MemoryDirector/blob/main/infra/terraform/projects/config/memory-director.json)
  and [read-only preference transport](https://github.com/afaryy/MemoryDirector/blob/main/services/api/app/preferences.py).
- [ClickHouse proof boundary](../clickhouse-mcp-proof.md) documents the fixed
  query, private authentication, and safe evidence fields.
- [Authenticated `run_query` smoke](https://github.com/afaryy/MemoryDirector/actions/runs/34002370165)
  completed against the hosted MCP service.
- The [Agent Engine smoke](https://github.com/afaryy/MemoryDirector/actions/runs/34024861486)
  also required `preference_tool_invoked: true` before activating the API.

Final-demo proof: capture the user action, the friendly preference explanation,
and a sanitized indication that the official MCP tool ran. Never show a
credential, bearer token, raw database response, or arbitrary SQL console.

## Supporting engineering evidence

These items strengthen technological implementation. They are not separate
prize categories in the official rules and must not be described as bonuses.

| Capability | Truthful status | Public evidence | Permitted submission wording |
| --- | --- | --- | --- |
| Terraform | Implemented, validated and used for sandbox infrastructure | [Terraform workflow](https://github.com/afaryy/MemoryDirector/actions/runs/34113891154), [roots and modules](https://github.com/afaryy/MemoryDirector/tree/main/infra/terraform) | “Terraform provisions the bounded Google Cloud sandbox.” |
| GitHub Actions and keyless deployment | Implemented; workflows use GitHub OIDC/WIF | [Application workflow](https://github.com/afaryy/MemoryDirector/blob/main/.github/workflows/deploy.yml), [current base test run](https://github.com/afaryy/MemoryDirector/actions/runs/34124916579) | “Tests and guarded deployments run through GitHub Actions using short-lived Google Cloud credentials.” |
| Consent gates | Implemented in Web and API; hosted consent-writer deployment exists | [Web gate](https://github.com/afaryy/MemoryDirector/blob/main/apps/web/src/components/ProductionWizard.tsx), [API guardian](https://github.com/afaryy/MemoryDirector/blob/main/services/api/app/consent_guardian.py), [consent-writer deployment](https://github.com/afaryy/MemoryDirector/actions/runs/34006128081) | “Media processing and export fail closed without the required consent decisions.” |
| Private Cloud Storage handling | Implemented in code and Terraform; final recording must use approved fixtures | [Storage adapter](https://github.com/afaryy/MemoryDirector/blob/main/services/api/app/media_storage.py), [storage infrastructure](https://github.com/afaryy/MemoryDirector/blob/main/infra/terraform/modules/foundations/sandbox_platform/main.tf), [retention operations](../operations/USAGE_COST_CONTROLS.md) | “Consented originals use private Cloud Storage; raw media is not stored in ClickHouse.” |
| Agent Engine | Hosted smoke verified and API activation gated on success | [Run 34024861486](https://github.com/afaryy/MemoryDirector/actions/runs/34024861486), [operations guide](../operations/AGENT_ENGINE.md) | Use the runtime claim above. |
| Lyria original memory song | Implemented with prompt-safety and fallback; hosted synthetic API render documented; final user-facing recording still required | [Lyria client](https://github.com/afaryy/MemoryDirector/blob/main/services/api/app/lyria_client.py), [song boundary](https://github.com/afaryy/MemoryDirector/blob/main/services/api/app/memory_song.py), [deployment evidence](../operations/APP_DEPLOYMENT.md) | Claim the song only if the final approved-fixture rehearsal and recording both succeed; otherwise show instrumental or no sound. |
| Video Intelligence | **Not implemented or runtime-verified** | No runtime dependency, call path, workflow or evidence artefact exists on audited `main` | Do not list, mention, imply, or select Video Intelligence in the submission. |
| Usage, rate-limit, cost and retention controls | Technical quotas, Cloud Armor and retention are deployed; billing controls have their own evidence status | [Control runbook](../operations/USAGE_COST_CONTROLS.md), [public-edge run](https://github.com/afaryy/MemoryDirector/actions/runs/34118291595) | Describe only the controls explicitly marked verified in the runbook. Do not claim an instantaneous hard cloud-spend guarantee. |

## Data sources and rights

The product uses only these data classes:

- photos and videos deliberately selected by the user;
- the user's typed or spoken production request;
- anonymised consent, render, and accepted/rejected preference events in
  ClickHouse;
- Gemini outputs derived from approved inputs and, only if the release gate
  passes, Lyria outputs derived from approved prompt context; and
- team-owned, synthetic, public-domain, or separately licensed demo assets.

The final demo is blocked until every visible or audible asset is approved in
[`MEDIA_RIGHTS_REGISTER.md`](../demo/MEDIA_RIGHTS_REGISTER.md). That includes
photos, clips, narration, ambient audio, generated music, cover art, logos, and
anything visible in screen-recording notifications or browser tabs.

For a generated song, record the model/version, approved prompt context,
safety result, duration, generation date, and available provenance. Do not call
generated output copyright-free, exclusive, or a licensed commercial song.

## Claims that require final artefacts

Do not mark these complete from code or workflow evidence alone:

- [ ] Devpost team roster contains at most four eligible members and names the
  authorised representative.
- [ ] ClickHouse is selected as the partner track.
- [ ] Rights register is complete and approved by the media owner.
- [ ] The exact approved fixture set succeeds through the hosted Web journey.
- [ ] The final video shows the product functioning, includes English audio or
  subtitles, and measures no more than 3:00.
- [ ] The video is publicly playable on YouTube or Vimeo.
- [ ] The final Devpost description matches the recorded build and lists all
  external data sources.
- [ ] App, health route, repository, licence, and video open from a signed-out
  or incognito browser.
- [ ] Submission receipt is retained before 9 September 2026, 2:00 PM PDT.

## Final evidence manifest

Complete this table during the release rehearsal. Do not commit secrets,
private media, private object URLs, or unsanitized logs.

| Artefact | Required value | Owner | Status |
| --- | --- | --- | --- |
| Release commit | Full commit SHA used for the hosted demo | Engineering | Pending final merge/deploy |
| Test run | Successful `Tests` workflow for the release commit | Engineering | Pending final commit |
| Hosted app | <https://memorydirector.com/> | Engineering | Available; final incognito check pending |
| Hosted health | <https://memorydirector.com/api/health> | Engineering | Available; final incognito check pending |
| Agent/MCP proof | Sanitized run or recording frame showing Agent Engine plus official MCP invocation | Demo recorder | Existing workflow proof; final recording frame pending |
| Rights approval | Completed rights register with owner and review date | Media owner | Pending |
| Demo duration | Measured `MM:SS` at or below `03:00` | Demo editor | Pending |
| Public video | YouTube or Vimeo URL | Devpost representative | Pending |
| Devpost entry | Public project URL and submission receipt | Devpost representative | Pending |

## Pre-publication redaction check

- Remove Secret Manager values, MCP bearer tokens, Google identity tokens,
  private GCS URIs, signed URLs, billing identifiers, email addresses, and
  personal notifications.
- Crop browser account avatars and unrelated tabs.
- Show only allow-listed, human-readable evidence fields: workflow URL, commit,
  tool name, hashed query identifier, row count, duration, and pass/fail result.
- Confirm no third-party logo, advertising, slogan, face, voice, or personal
  detail appears without recorded permission.
