# Current capability evidence

This matrix is the source of truth for claims in the active product, architecture,
operations, demo, and submission documentation. It was reconciled on 8 September
2026 against `origin/main` at `cc6c10267f9294e28ce8fb4b0a6b030529a7ca8b`.
The public product at [memorydirector.com](https://memorydirector.com/) runs the
Web release `64ee654a999549322dbeea22f9ffc2b8b29acdaf`.

Evidence levels are intentionally separate:

- **Implemented** means code and automated tests exist on the audited commit.
- **Deployed** means a production workflow or browser check exercised that commit.
- **Physical device** means the native picker, touch, download, or share behaviour
  has been checked on real iOS or Android hardware.
- **Final submission** means the rights-cleared media, final recording, and submitted
  Devpost entry exist. Implementation or deployment alone does not prove this level.

| Capability | Implemented | Deployed | Physical device | Final submission | Evidence / owner |
| --- | --- | --- | --- | --- | --- |
| Public web app and same-origin health route | Verified | Verified | Not required | Available for final entry | [Web application](../apps/web/src/app/page.tsx), [deployment workflow](../.github/workflows/deploy.yml), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Select mixed photos and videos; append more, reject duplicates, and clear all | Verified | Verified in desktop and mobile emulation | Pending ST-52 | Not required | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [wizard tests](../apps/web/src/components/ProductionWizard.test.tsx), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Reorder media and choose the cover | Verified | Verified in browser | Touch gesture pending ST-52 | Not required | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [wizard tests](../apps/web/src/components/ProductionWizard.test.tsx) |
| Describe the memory by text or voice | Verified | Text verified in browser | Voice permission and recording pending ST-52 | Not required | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Explicit media consent before production | Verified | Verified in browser | Pending ST-52 journey | Required behaviour, not submission evidence | [API consent guardian](../services/api/app/consent_guardian.py), [guardian tests](../services/api/tests/test_consent_guardian.py), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Original memory song, gentle instrumental, or no music | Verified | Original-song and no-music paths verified; instrumental rerun pending ST-52 | Pending ST-52 | Final recording must show only a verified path | [Memory-song adapter](../services/api/app/memory_song.py), [production wizard](../apps/web/src/components/ProductionWizard.tsx), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Public Web storyboard planning through direct Gemini | Verified | Verified in hosted browser journeys | Not required | Final recording pending ST-17 | [Web call path](../apps/web/src/components/ProductionWizard.tsx), [storyboard endpoint](../services/api/app/main.py), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Agent Engine creates a schema-valid 60-second production plan | Verified | Verified by deployment smoke | Not required | Evidence ready | [Agent Engine adapter](../services/api/app/agent_engine.py), [Agent Engine workflow](../.github/workflows/deploy-agent-engine.yml), [operations evidence](operations/AGENT_ENGINE.md) |
| Agent Engine invokes the approved ClickHouse MCP preference tool | Verified | Verified by deployment smoke | Not required | Evidence ready | [Preference tool](../services/api/app/clickhouse_preferences.py), [Agent Engine workflow](../.github/workflows/deploy-agent-engine.yml), [operations evidence](operations/AGENT_ENGINE.md) |
| ClickHouse MCP guards consent/export and records scoped events | Verified | Verified in hosted journey | Not required | Evidence ready | [Consent guardian](../services/api/app/consent_guardian.py), [event writer](../services/consent-writer/app/repository.py), [ClickHouse workflow](../.github/workflows/clickhouse.yml) |
| Deterministic vertical MP4 render with 60-second duration verification | Verified | Verified for original-song and no-music journeys | Not required | Final recording pending ST-17 | [Render service](../services/api/app/render.py), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Inline preview, playback, cover frame, progress, and Make again | Verified | Verified in desktop and mobile emulation | Touch playback pending ST-52 | Final recording pending ST-17 | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Save video | Verified | Browser UI verified | Filesystem result pending ST-52 | Final recording pending ST-17 | [Wizard tests](../apps/web/src/components/ProductionWizard.test.tsx), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Share video through the native share sheet, with a save-first fallback | Verified by component test | UI deployed; native sharing not exercised | Completion and cancellation pending ST-52 | Final recording may show only verified behaviour | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [wizard tests](../apps/web/src/components/ProductionWizard.test.tsx), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Accessible contrast, labels, keyboard focus, responsive layout, and reduced motion | Verified | Verified in production at desktop and 390 x 844 | Pending ST-52 | Evidence ready for browser scope | [Accessibility regression](qa/ST-31-visual-accessibility-regression.md), [wizard tests](../apps/web/src/components/ProductionWizard.test.tsx) |
| Four-layer usage and cost controls | Application quotas, edge limits, compute bounds, retention, and budget configuration verified | Technical controls active; alerts and spend caps recorded as configured, not instantaneous | Not required | Evidence ready only with the stated billing limitation | [Usage and cost controls](operations/USAGE_COST_CONTROLS.md), [deployment workflow](../.github/workflows/deploy.yml) |
| Real iOS and Android journey | Not a code capability | Not proven by emulation | Pending ST-52 | Pending ST-52 | [ST-49 handoff](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) — Yvonne |
| Rights-cleared final demo media | Eight fixtures and the generated song are recorded and approved | Final 60-second export reviewed | Owner accepted incidental-background risk and approved the complete song | Evidence ready; keep private artefacts private | [Media rights register](demo/MEDIA_RIGHTS_REGISTER.md) — Yvonne |
| Final English demo video, at most three minutes | Script and runbook exist | Not applicable | Depends on ST-52 evidence | Pending ST-17 | [Demo script](submission/DEMO_SCRIPT.md), [demo runbook](demo/DEMO_RUNBOOK.md) — Yvonne |
| Devpost entry and submission confirmation | Draft package exists | Not applicable | Not applicable | Pending final submission checklist | [Submission checklist](submission/SUBMISSION_CHECKLIST.md), [evidence package](submission/EVIDENCE_PACKAGE.md) — Yvonne; also depends on ST-9, ST-17, ST-52, roster, eligibility, track selection, public video, form review, and receipt |

The deployed browser evidence does not imply full phone-library access, direct
posting to social networks, completed physical-device QA, a finished three-minute
video, or instantaneous billing enforcement. Those boundaries stay explicit until
the linked follow-up evidence exists.
