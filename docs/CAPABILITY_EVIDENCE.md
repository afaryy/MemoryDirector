# Current capability evidence

This matrix is the source of truth for claims in the active product, architecture,
operations, demo, and submission documentation. It was reconciled on 8 September
2026 against `origin/main` at `eab585c9f8db6bbf14143c8e5c61c24c7cf2ecca`,
which passed [Tests run 34191468668](https://github.com/afaryy/MemoryDirector/actions/runs/34191468668).
The public product at [memorydirector.com](https://memorydirector.com/) runs Web
release `6b738f40014e4c7861ff1705f7df4d26d294d051`, deployed by
[run 34188310631](https://github.com/afaryy/MemoryDirector/actions/runs/34188310631).

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
| Select mixed photos and videos; append more, reject duplicates, and clear all | Verified | Verified in desktop and mobile emulation | Passed on iPhone 11 | Not required | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [wizard tests](../apps/web/src/components/ProductionWizard.test.tsx), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md), [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Local video frame with private mobile thumbnail fallback | Verified; desktop stays local-only and mobile fallback is consent-gated | Deployed in `6b738f4` | Phone-video preview passed on iPhone 11 | Not required | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [thumbnail API](../services/api/app/media_thumbnail.py), [architecture](ARCHITECTURE.md), [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Reorder media and choose the cover | Verified | Verified in browser | Touch reorder passed on iPhone 11 | Not required | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [wizard tests](../apps/web/src/components/ProductionWizard.test.tsx), [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Describe the memory by text or voice | Verified | Text verified in browser | Microphone, speech, correction, and Clear passed on iPhone 11 | Not required | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md), [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Explicit media consent before production | Verified | Verified in browser | Passed in the iPhone journey | Required behaviour, not submission evidence | [API consent guardian](../services/api/app/consent_guardian.py), [guardian tests](../services/api/tests/test_consent_guardian.py), [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Original memory song, gentle instrumental, or no music | Verified | Original-song and no-music paths verified in ST-49; instrumental path verified in ST-52 | Instrumental render and audio passed on iPhone 11 | Final recording must show only a verified path | [Memory-song adapter](../services/api/app/memory_song.py), [production wizard](../apps/web/src/components/ProductionWizard.tsx), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md), [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Public Web storyboard planning through direct Gemini | Verified | Verified in hosted browser journeys | Not required | Final recording pending ST-17 | [Web call path](../apps/web/src/components/ProductionWizard.tsx), [storyboard endpoint](../services/api/app/main.py), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Agent Engine creates a schema-valid 60-second production plan | Verified | Verified by deployment smoke | Not required | Evidence ready | [Agent Engine adapter](../services/api/app/agent_engine.py), [Agent Engine workflow](../.github/workflows/deploy-agent-engine.yml), [operations evidence](operations/AGENT_ENGINE.md) |
| Agent Engine invokes the approved ClickHouse MCP preference tool | Verified | Verified by deployment smoke | Not required | Evidence ready | [Preference tool](../services/api/app/clickhouse_preferences.py), [Agent Engine workflow](../.github/workflows/deploy-agent-engine.yml), [operations evidence](operations/AGENT_ENGINE.md) |
| ClickHouse MCP guards consent/export and records scoped events | Verified | Verified in hosted journey | Not required | Evidence ready | [Consent guardian](../services/api/app/consent_guardian.py), [event writer](../services/consent-writer/app/repository.py), [ClickHouse workflow](../.github/workflows/clickhouse.yml) |
| Deterministic vertical MP4 render with 60-second duration verification | Verified | Verified for original-song and no-music journeys | Not required | Final recording pending ST-17 | [Render service](../services/api/app/render.py), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md) |
| Inline preview, playback, cover frame, progress, and Make again | Verified | Verified in desktop and mobile emulation | Phone preview and touch interactions passed on iPhone 11 | Final recording pending ST-17 | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [ST-49 browser acceptance](qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md), [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Save video | Verified | Browser UI verified | Saved MP4 appeared in the expected location on iPhone 11 | Final recording pending ST-17 | [Wizard tests](../apps/web/src/components/ProductionWizard.test.tsx), [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Share video through the native share sheet, with a save-first fallback | Verified by component test | UI deployed | Native sheet and installed-destination behavior passed on iPhone 11 | Final recording may show only verified behaviour | [Production wizard](../apps/web/src/components/ProductionWizard.tsx), [wizard tests](../apps/web/src/components/ProductionWizard.test.tsx), [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Accessible contrast, labels, keyboard focus, responsive layout, and reduced motion | Verified | Verified in production at desktop and 390 x 844 | Core device interactions passed; native screen reader not tested | Evidence ready for browser scope | [Accessibility regression](qa/ST-31-visual-accessibility-regression.md), [wizard tests](../apps/web/src/components/ProductionWizard.test.tsx), [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Four-layer usage and cost controls | Application quotas, edge limits, compute bounds, retention, and budget configuration verified | Technical controls active; alerts and spend caps recorded as configured, not instantaneous | Not required | Evidence ready only with the stated billing limitation | [Usage and cost controls](operations/USAGE_COST_CONTROLS.md), [deployment workflow](../.github/workflows/deploy.yml) |
| Real iPhone journey | Not a code capability | Not proven by emulation | Passed on iPhone 11, iOS 26.6.1, Chrome (version not recorded) | Evidence ready; final recording still pending | [ST-52 iPhone acceptance](qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) |
| Real Android journey | Not a code capability | Not proven by emulation | Not tested | Not required for the Web entry | No Android claim is made |
| Rights-cleared final demo media | Eight fixtures and the generated song are recorded and approved | Final 60-second export reviewed | Owner accepted incidental-background risk and approved the complete song | Evidence ready; keep private artefacts private | [Media rights register](demo/MEDIA_RIGHTS_REGISTER.md) — Yvonne |
| Final English demo video, at most three minutes | Script and runbook exist | Not applicable | iPhone rehearsal evidence is ready | Pending ST-17 | Private demo script, [demo runbook](demo/DEMO_RUNBOOK.md) — Yvonne |
| Devpost entry and submission confirmation | Draft package exists | Not applicable | iPhone evidence ready | Pending final submission checklist | Private submission checklist, [evidence package](submission/EVIDENCE_PACKAGE.md) — Yvonne; also depends on ST-17, roster, eligibility, track selection, public video, form review, and receipt |

The deployed browser evidence does not imply full phone-library access, direct
posting to social networks, Android or native-screen-reader coverage, a finished
three-minute video, or instantaneous billing enforcement. Those boundaries stay
explicit until the linked follow-up evidence exists.
