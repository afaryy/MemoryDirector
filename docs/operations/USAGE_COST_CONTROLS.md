# Usage, Cost, Rate-Limit, and Retention Controls

Memory Director is intentionally available without an account during the public evaluation period. Four independent controls bound the cost and privacy risk of that guest-first experience. No single control is treated as a complete safeguard.

## Configuration ownership

| File or control plane | Owns | Must not contain |
| --- | --- | --- |
| `infra/terraform/projects/config/common-environment.json` | Product-wide ceilings: 60-second output, 15 media items, upload/request limits, and the global daily hard maximum of 100 | Project credentials or environment-specific quotas |
| `infra/terraform/projects/config/sandbox.json` | Sandbox quotas, Cloud Armor thresholds, Cloud Run scaling/concurrency, and application-media retention | Secrets or Terraform state retention |
| `infra/terraform/projects/config/memory-director.json` | `memory-director-505708`, public edge, and the approved USD budget targets | Passwords, API tokens, or generated secret values |
| `infra/terraform/projects/config/config.schema.json` | Types, required fields, minimums, maximums, and closed-object validation | Runtime values that bypass reviewed JSON |
| Google Secret Manager | Cookie/demo signing material and provider credentials | Non-sensitive quota numbers |
| Cloud Billing | Alerts-only budget and eligible-service spend caps | Application quota state |

GitHub Actions selects the project and environment configuration, validates them, and runs Terraform. GitHub repository or environment variables are not a second source of truth for these numbers. Terraform converts approved values to Cloud Run environment variables only at the service boundary.

## Layer 1: application admission quotas

The sandbox admits at most five film attempts per browser visitor and ten per client IP per UTC day. No IP can hold more than two film leases, no more than six film leases can be active globally, and the sandbox initially admits thirty film attempts per UTC day. The schema forbids configuring more than one hundred per day.

Original-song work has tighter limits: three attempts per visitor and twenty globally per UTC day. An admitted attempt is counted before Gemini, Lyria, or ffmpeg starts and is not refunded after a downstream failure; this prevents repeatedly failing requests from becoming a cost bypass. The concurrency portion of the lease is always released.

Firestore Native mode is the authoritative transactional quota store shared by every Cloud Run instance. Identifiers are hashed before document keys are written. ClickHouse receives bounded decision and outcome telemetry for cost analysis, but it is not used as an atomic admission counter.

The browser reserves one short-lived admission before it uploads media or invokes Gemini. The same opaque admission ID is required for the bounded workflow: media analyses up to the configured media-item limit, one planning operation, one export, and—only when the admission reserved an original song—one song generation. Media analysis is idempotent by content ID, so the client's bounded retry of the same file does not consume another slot. Stage use is consumed atomically in Firestore, an export is terminal, and a no-sound or instrumental admission cannot be upgraded to an original song. The lease is released when the workflow succeeds or fails. Expired leases are reclaimed so a terminated Cloud Run instance cannot hold capacity for the rest of the day. Rejected or replayed requests return HTTP 429 before a costly provider call starts.

## Layer 2: edge and compute protection

Cloud Armor applies layered per-IP throttles at the external Application Load Balancer:

- 120 public requests per minute;
- 30 `/api/` requests per minute;
- 5 costly render or original-song requests per ten minutes;
- HTTP 429 when exceeded, with a one-hour rate-limit ban where supported.

These thresholds absorb bursts and automated abuse. Daily quotas remain application-enforced because edge rate limiting is not the business usage ledger.

Cloud Run keeps zero minimum instances. The web service is limited to two instances at concurrency eighty. The rendering API is limited to three instances, concurrency four, and a 900-second request timeout. Maximum instances constrain concurrency and infrastructure expansion, not monthly model spend.

### Verified sandbox state — 7 September 2026

The Cloud Armor policy is active on both public load-balancer backends. The
deployed rules match the reviewed sandbox values above, including the
high-cost route rule, broader API rule, general public rule, HTTP 429 response,
and one-hour ban. Public-edge workflow run
[34118291595](https://github.com/afaryy/MemoryDirector/actions/runs/34118291595)
completed with one resource added, two updated in place, and zero destroyed.
Anonymous HTTPS checks returned HTTP 200 for the homepage and `/api/health`.

The first production attempt exposed a missing Cloud Armor provisioning
permission. PR
[#109](https://github.com/afaryy/MemoryDirector/pull/109) added the documented
operator-only role after Terraform tests and review. The next attempt exposed a
Cloud Armor expression that used a forbidden regular-expression capture group;
PR [#110](https://github.com/afaryy/MemoryDirector/pull/110) replaced it with
explicit path predicates and added a regression test. Neither application
runtime identity received the provisioning role.

## Layer 3: billing protection

The approved monthly currency is USD:

| Control | Amount | Enforcement |
| --- | ---: | --- |
| Absolute cost tolerance | 200 | Governance boundary, not an instantaneous guarantee |
| Whole-project alert budget | 150 | Alerts only |
| Eligible Vertex AI spend-cap target | 110 | Pauses eligible new Vertex AI usage when enforced |
| Eligible Cloud Run spend-cap target | 25 | Pauses eligible new Cloud Run usage when enforced |
| Reserved buffer | 50 | Storage, load balancing, logging, in-flight work, and reporting delay |

Google Cloud spend-cap budgets are Preview, are scoped to one project and one eligible service, and are not instantaneous. In-flight work and persistent resources can continue accruing charges. For that reason the project operates below the USD 200 tolerance and relies on admission quotas as the immediate control.

The spend caps and project budget are not considered active until an operator records the Cloud Billing budget names, scopes, status, and notification recipients. ClickHouse Cloud billing is separate and is not included in the USD 200 Google Cloud tolerance.

As of 7 September 2026, the technical quota, Cloud Run, Cloud Armor, Firestore,
and GCS controls are deployed. Billing protection remains unverified because
the Cloud Billing Budget API is not enabled for the operator's quota project
and billing-budget access could not be confirmed. ST-45 must remain In Progress
until the three billing controls below have visible, non-sensitive evidence.

### Billing-console activation evidence

1. Open Cloud Billing > Budgets & alerts for the billing account linked to `memory-director-505708`.
2. Create an alerts-only project budget for USD 150 with thresholds at 50%, 75%, 90%, and 100%.
3. Create a spend-cap budget scoped to `memory-director-505708` and the eligible Vertex AI/Agent Platform service for USD 110.
4. Create a spend-cap budget scoped to `memory-director-505708` and Cloud Run for USD 25.
5. Record screenshots or exported metadata showing each name, project, service, amount, currency, and configured status; never include payment details.
6. Do not mark ST-45 complete until the controls are visible and a non-destructive verification has been recorded.

## Layer 4: private-media retention

The application GCS bucket enforces public access prevention and uniform bucket-level access. Prefix-scoped lifecycle deletion applies only to application objects:

- `media/` uploads and decisions: delete after one day;
- `exports/` previews, videos, covers, captions, and bundles: delete after three days.

Terraform state uses its independent bootstrap bucket and is never passed to the media lifecycle module. Destroying sandbox application resources does not authorize deletion of bootstrap state. Signed upload/download URLs are not claimed by this control set because the current application still uses the API upload/export path.

## Change and emergency procedure

1. Change the owning JSON file; never patch deployed Cloud Run variables by hand.
2. Run JSON Schema tests, API tests, Terraform tests, formatting, lint/build, and security scanning.
3. Review the Terraform plan and confirm the target project is exactly `memory-director-505708`.
4. Merge only after PR review and all required checks pass.
5. Deploy the relevant `platform`, `app`, or `public-edge` component through its guarded workflow.
6. Verify Cloud Run revisions, Firestore quota records, backend security policies, GCS lifecycle rules, and an HTTP 429 boundary response.

For an active cost incident, first disable quota admission or set the daily limit to the lowest schema-valid value and deploy the API. If abuse continues, use the public-edge workflow to deny costly routes or temporarily remove public access. Spend-cap enforcement can pause eligible services but must not be the only emergency action.
