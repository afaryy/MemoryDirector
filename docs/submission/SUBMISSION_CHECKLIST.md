# ST-32 competition compliance checklist

Last revalidated: **7 September 2026 (AEST)** against repository commit
`1d2947154bfe523139d837070f63b1af5afb4e71` and the live Devpost pages.

Status meanings:

- **Verified** — the linked public evidence was checked during this audit.
- **Ready** — repository material exists, but the final submission must include it.
- **Blocked** — a human action or final artefact is still missing.
- **Attestation required** — the repository cannot prove the entrant's eligibility
  or authority.

## Source of truth

Use the [official rules](https://agentic-cinema.devpost.com/rules) where the
overview or an older repository note conflicts with them. The live rules,
[schedule](https://agentic-cinema.devpost.com/details/dates), and
[overview](https://agentic-cinema.devpost.com/) all currently show the same
deadline: **9 September 2026 at 2:00 PM Pacific Daylight Time**. That is
**10 September 2026 at 7:00 AM AEST (Melbourne)**.

The earlier September 7 date recorded in this repository is obsolete. Recheck
the live rules immediately before the final Devpost submission.

## Compliance matrix

| Requirement | Official source | Exact proof to submit or retain | Status | Owner | Blocker / next action |
| --- | --- | --- | --- | --- | --- |
| Submit before 9 Sep 2026, 2:00 PM PDT | [Rules, sections 5 and 7](https://agentic-cinema.devpost.com/rules); [schedule](https://agentic-cinema.devpost.com/details/dates) | Devpost confirmation before 10 Sep, 7:00 AM AEST | Ready | Devpost representative | Submit early enough to recover from upload or form errors. |
| Every entrant is eligible | [Rules, section 4](https://agentic-cinema.devpost.com/rules) | Each member confirms age, residence, sanctions-list and contest-entity eligibility | Attestation required | Every team member | Repository evidence cannot establish personal eligibility. |
| No more than four people; every member added on Devpost; one authorised representative | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules) | Screenshot or final review of the Devpost member list and named representative | Blocked | Devpost representative | Verify the live Devpost roster; do not infer it from GitHub or Linear. |
| Functional production-ready agent powered by Gemini and Google Cloud Agent Builder | [Rules, section 7.A](https://agentic-cinema.devpost.com/rules) | Hosted flow in the demo; source paths for ADK/Agent Engine and Gemini; successful [Agent Engine deployment and smoke run](https://github.com/afaryy/MemoryDirector/actions/runs/34024861486) | Verified | Engineering | The run proves the hosted Agent Engine plan and tool invocation; the final video must show the user-facing workflow. |
| Active ClickHouse use at runtime through official `mcp-clickhouse`, connected to Cloud or self-hosted ClickHouse | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules); [ClickHouse track resources](https://agentic-cinema.devpost.com/details/clickhouse-resources) | `mcp-clickhouse` image/config in source; runtime call shown in the final demo; successful Agent Engine smoke step named “Prove Agent Engine plan and ClickHouse preference-tool invocation” | Verified | Engineering / demo recorder | Keep the MCP call visible and explain its actual preference/consent role; a README mention alone is insufficient. |
| Only Google Cloud AI and the chosen partner's built-in AI features are used by the submitted product | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules) | Runtime dependency and architecture review; final copy contains no unsupported AI claim | Verified | Engineering / submission editor | Current runtime code uses Google ADK, Vertex AI/Gemini and ClickHouse; re-scan dependencies and submission copy after later merges. |
| Project runs on web, Android or iOS | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules) | Public web URL and demo footage | Verified | Engineering | [Hosted web app](https://memorydirector.com/) returned HTTP 200 on 7 Sep 2026. |
| Project is new, original work created during the contest period | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules) | Repository creation history plus entrant attestation that this is not an extension of earlier work | Attestation required | Devpost representative | Public repository metadata shows creation on 16 Aug 2026, but originality and prior-work status require human confirmation. |
| Hosted project URL is supplied for judging and testing | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules); [overview](https://agentic-cinema.devpost.com/) | `https://memorydirector.com/` in Devpost and an incognito check | Verified | Engineering / Devpost representative | Apex and `/api/health` returned HTTP 200 on 7 Sep 2026. Direct `run.app` URLs return 404 by design after ingress lockdown and must not be submitted. |
| English text description covers features, functionality, technologies, data sources, findings and learnings | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules) | Finalised [`DEVPOST_PROJECT_PAGE.md`](DEVPOST_PROJECT_PAGE.md) copied to Devpost | Ready | Submission editor | Refresh the draft after the final demo so it describes only reproducibly demonstrated capabilities. |
| Public source repository includes all source, assets and run instructions and demonstrates Google Cloud and partner runtime calls | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules) | [Public repository](https://github.com/afaryy/MemoryDirector), root README, source, Terraform, workflows and operations docs | Verified | Engineering | GitHub reports the repository as public. Perform one final clean-clone instructions check after the last merge. |
| Public repository has a visible OSI-approved licence permitting commercial use | [Rules, sections 7.B and 12](https://agentic-cinema.devpost.com/rules); [overview](https://agentic-cinema.devpost.com/) | Root [`LICENSE`](../../LICENSE) and GitHub licence detection | Verified | Engineering | GitHub detects the root file as MIT. Confirm it remains visible at the top of the repository page. |
| ClickHouse partner track is selected | [Overview submission requirements](https://agentic-cinema.devpost.com/) | Final Devpost track field set to ClickHouse | Blocked | Devpost representative | Must be selected in the Devpost form; repository metadata cannot prove the form value. |
| Public demo shows the project functioning as built | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules); [overview](https://agentic-cinema.devpost.com/) | Final hosted-product recording following [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) | Blocked | Demo recorder | Record the actual flow after final production smoke checks; do not substitute slides or an API-only test. |
| Demo is no longer than three minutes, public on YouTube or Vimeo, and English or English-subtitled | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules) | Public YouTube/Vimeo URL, duration at or below 3:00, captions checked | Blocked | Demo editor / Devpost representative | Video has not been recorded and published. Aim below 2:55 to leave margin. |
| Written submission is English and product supports English | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules) | English Devpost page, English demo/captions and English product path | Ready | Submission editor / QA | The repository and UI support English; verify the final deployed path and all form fields. |
| Third-party SDKs, APIs and data are authorised under their terms | [Rules, section 7.B](https://agentic-cinema.devpost.com/rules) | Dependency inventory and evidence that team accounts/assets may be used in the submission | Attestation required | Engineering lead / Devpost representative | Confirm account terms and any non-code data sources before submission. |
| Video and project assets are original or authorised and do not violate privacy, publicity, trademark or IP rights | [Rules, sections 7.B and 15](https://agentic-cinema.devpost.com/rules) | Completed [`MEDIA_RIGHTS_REGISTER.md`](../demo/MEDIA_RIGHTS_REGISTER.md), consent/licence evidence and final-frame review | Blocked | Media owner / demo editor | The rights register is still blank. Also remove incidental third-party logos, advertising and private information from footage. |
| Completed Devpost form contains every required field and no secrets/private media | [Overview submission requirements](https://agentic-cinema.devpost.com/); [rules, section 6](https://agentic-cinema.devpost.com/rules) | Final form review, public links opened incognito, submission receipt | Blocked | Devpost representative | Requires the final video URL, track choice, roster check and submission action. |

## Repository evidence checked

- Public repository and MIT licence:
  <https://github.com/afaryy/MemoryDirector>
- Hosted product: <https://memorydirector.com/>
- Hosted health route: <https://memorydirector.com/api/health>
- Latest `main` test run at audit time:
  <https://github.com/afaryy/MemoryDirector/actions/runs/34119555723>
- Hosted Agent Engine and ClickHouse preference-tool smoke:
  <https://github.com/afaryy/MemoryDirector/actions/runs/34024861486>
- Public-edge deployment and HTTPS verification:
  <https://github.com/afaryy/MemoryDirector/actions/runs/34118291595>
- Agent runtime boundary and evidence criteria:
  [`docs/operations/AGENT_ENGINE.md`](../operations/AGENT_ENGINE.md)
- ClickHouse MCP boundary:
  [`docs/clickhouse-mcp-proof.md`](../clickhouse-mcp-proof.md)

## Final release sequence

1. Complete and approve the media rights register.
2. Verify the Devpost roster, eligibility attestations, representative and
   ClickHouse track selection.
3. Run the hosted flow with the exact approved demo fixtures and capture the
   runtime ClickHouse/Agent Engine evidence without exposing credentials.
4. Record and publish an English or English-subtitled YouTube/Vimeo demo under
   three minutes.
5. Refresh the project-page copy so every capability matches the final build.
6. Open the app, health route, repository, licence and video from an incognito
   session, then submit before the deadline and retain the receipt.
