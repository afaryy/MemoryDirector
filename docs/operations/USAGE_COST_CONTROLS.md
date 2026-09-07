# Usage, Cost, Rate-Limit, and Retention Controls

Memory Director is intentionally available without an account during the public evaluation period. Four independent controls bound the cost and privacy risk of that guest-first experience. No single control is treated as a complete safeguard.

## Configuration ownership

| File or control plane | Owns | Must not contain |
| --- | --- | --- |
| `infra/terraform/projects/config/common-environment.json` | Product-wide ceilings: 60-second output, 15 media items, upload/request limits, and the global daily hard maximum of 100 | Project credentials or environment-specific quotas |
| `infra/terraform/projects/config/sandbox.json` | Sandbox quotas, Cloud Armor thresholds, Cloud Run scaling/concurrency, and application-media retention | Secrets or Terraform state retention |
| `infra/terraform/projects/config/memory-director.json` | `memory-director-505708`, public edge, and the approved AUD budget targets | Passwords, API tokens, or generated secret values |
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

The linked Cloud Billing account and all approved monthly controls use AUD:

| Control | Amount | Enforcement |
| --- | ---: | --- |
| Absolute cost tolerance | A$250 | Governance boundary, not an instantaneous guarantee |
| Whole-project alert budget | A$200 | Alerts only |
| Eligible Vertex AI / Agent Platform spend-cap target | A$150 | Pauses eligible new usage when enforced |
| Eligible Cloud Run spend-cap target | A$35 | Pauses eligible new usage when enforced |
| Reserved buffer | A$50 | Storage, load balancing, logging, in-flight work, and reporting delay |

Google Cloud spend-cap budgets are Preview, are scoped to one project and one eligible service, and are not instantaneous. In-flight work and persistent resources can continue accruing charges. Spend caps must be created in the Cloud Billing console by selecting **Spend cap enforcement**; the Budget API and `gcloud billing budgets` create alerts-only budgets. For that reason the project operates below the A$250 tolerance and relies on admission quotas as the immediate control. See Google's [spend-cap documentation](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

Each spend cap is considered active only after an operator records its Cloud Billing name, project, service, amount, configured status, and notification recipients. ClickHouse Cloud billing is separate and is not included in the A$250 Google Cloud tolerance.

As of 7 September 2026, the technical quota, Cloud Run, Cloud Armor, Firestore,
and GCS controls are deployed. The Cloud Billing Budget API is enabled and the
alerts-only budget below is active. The two spend-cap controls remain pending
until their console status has been verified. ST-45 must remain In Progress
until all three billing controls have visible, non-sensitive evidence.

### Verified alerts-only budget — 7 September 2026

- Name: `Memory Director project alert`
- Resource: `billingAccounts/01ABF0-FE72D6-AD545C/budgets/fba17495-d534-4022-b5cd-2f1856afb2ec`
- Scope: project number `192915586401` (`memory-director-505708`)
- Amount and period: A$200 per month
- Thresholds: 50%, 80%, and 100% of current spend
- Credits: all credits included

### Billing-console activation evidence

1. Open Cloud Billing > Budgets & alerts for the billing account linked to `memory-director-505708`.
2. Confirm the existing A$200 alerts-only project budget and its notification recipients.
3. In the console, create a spend-cap budget scoped to `memory-director-505708` and the eligible Vertex AI / Agent Platform service for A$150.
4. In the console, create a spend-cap budget scoped to `memory-director-505708` and Cloud Run for A$35.
5. Record screenshots or exported metadata showing each name, project, service, amount, currency, configured status, and notification recipients; never include payment details.
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
