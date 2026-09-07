# ST-45 Four-Layer Usage and Cost Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound public Memory Director usage, infrastructure load, monthly Google Cloud spend, and private-media retention with reviewed, reproducible configuration.

**Architecture:** Checked-in JSON is the non-sensitive source of truth and is constrained by JSON Schema. Terraform merges common, sandbox, and project configuration into Cloud Run, Cloud Armor, Firestore, and GCS resources; FastAPI acquires a Firestore transaction-backed quota lease before any costly song or render operation and always releases concurrency. ClickHouse remains the evidence/analytics path, while Cloud Billing Preview spend caps are configured and verified separately because they are a billing control-plane feature with delayed enforcement.

**Tech Stack:** Python 3.12, FastAPI, Google Cloud Firestore, Google Cloud Storage, ClickHouse telemetry, Terraform Google provider, Cloud Armor, Cloud Run, Node/Ajv JSON Schema validation, GitHub Actions.

**Spec:** `docs/operations/USAGE_COST_CONTROLS.md`

## Global Constraints

- Target only Google Cloud project `memory-director-505708` and repository `afaryy/MemoryDirector` (with the existing future `sailing-together/MemoryDirector` WIF allowance unchanged).
- Guest mode remains the default; this work does not add or require login.
- Non-sensitive values live in `infra/terraform/projects/config/*.json`; secrets live in Secret Manager.
- Maximum film length is 60 seconds and maximum media count is 15.
- Initial sandbox global daily admission limit is 30; JSON Schema forbids values above 100.
- Quota admission is shared across Cloud Run instances and happens before Gemini, Lyria, or ffmpeg work.
- Terraform state buckets are never covered by media lifecycle deletion.
- Do not claim that the A$250 tolerance is an instantaneous hard billing guarantee.

---

### Task 1: Configuration contract and operator documentation

**Files:**
- Create: `docs/operations/USAGE_COST_CONTROLS.md`
- Modify: `infra/terraform/projects/config/common-environment.json`
- Modify: `infra/terraform/projects/config/sandbox.json`
- Modify: `infra/terraform/projects/config/memory-director.json`
- Modify: `infra/terraform/projects/config/config.schema.json`
- Test: `infra/terraform/tools/config-validator/test/validate-config.test.mjs`

**Interfaces:**
- Produces: `application_limits`, `quotas`, `rate_limits`, `retention`, `cloud_run`, and `budgets` JSON objects consumed by Terraform roots.

- [ ] **Step 1: Add failing validator tests.** Test checked-in configuration, reject `global_daily_film_limit` above 100, reject budgets whose tolerance exceeds A$250, and reject retention rules that include the Terraform state bucket.
- [ ] **Step 2: Run `cd infra/terraform/tools/config-validator && npm test -- --run`.** Expect the new cases to fail because the schema does not know the approved objects.
- [ ] **Step 3: Add the exact approved values and schema bounds.** Keep project, environment, and common ownership separate and add semantic cross-file checks to `validate-config.mjs` only where JSON Schema cannot compare values.
- [ ] **Step 4: Write the operations document.** Include ownership, deployment flow, alert versus spend-cap behavior, emergency shutdown, and the explicit A$250 limitation.
- [ ] **Step 5: Re-run validator tests.** Expect all tests to pass.

### Task 2: Shared transactional quota gate

**Files:**
- Create: `services/api/app/usage_limits.py`
- Create: `services/api/tests/test_usage_limits.py`
- Modify: `services/api/pyproject.toml`
- Modify: `services/api/app/main.py`
- Test: `services/api/tests/test_memory_song_endpoint.py`
- Test: `services/api/tests/test_media_render_endpoint.py`

**Interfaces:**
- Produces: `UsagePolicy.from_environment()`, `QuotaStore.acquire(request) -> QuotaLease`, and `QuotaLease.release()`.
- Consumes: visitor cookie/header identity, trusted forwarded client IP, soundtrack mode, and approved JSON-derived Cloud Run environment variables.

- [ ] **Step 1: Write failing unit tests.** Prove visitor limit 5, IP limit 10, global limit 30, global configured maximum 100, per-IP concurrency 2, original-song limits, UTC-day isolation, and release on both success and exception.
- [ ] **Step 2: Run `cd services/api && uv run pytest tests/test_usage_limits.py -q`.** Expect import/behavior failures.
- [ ] **Step 3: Implement policy and an in-memory reference repository.** The reference repository supplies deterministic real-behavior tests; production construction must select Firestore when quotas are enabled.
- [ ] **Step 4: Implement Firestore transaction-backed acquire/release.** Hash visitor/IP identifiers before document keys; atomically increment daily admissions and in-flight counters; never decrement daily admitted work.
- [ ] **Step 5: Add endpoint failing tests.** Prove denied `/memory-songs` and `/renders/export` requests never call Lyria or renderer and that leases release after success/failure.
- [ ] **Step 6: Integrate the gate before costly dependencies.** Return HTTP 429 with a senior-readable message and `Retry-After`; always release concurrency in `finally`.
- [ ] **Step 7: Run API tests.** Expect all tests to pass.

### Task 3: Firestore, runtime limits, and private-media lifecycle

**Files:**
- Modify: `infra/terraform/modules/base/cloud_run_service/variables.tf`
- Modify: `infra/terraform/modules/base/cloud_run_service/main.tf`
- Modify: `infra/terraform/modules/base/private_media_bucket/variables.tf`
- Modify: `infra/terraform/modules/base/private_media_bucket/main.tf`
- Modify: `infra/terraform/modules/foundations/sandbox_platform/main.tf`
- Modify: `infra/terraform/modules/foundations/sandbox_platform/outputs.tf`
- Modify: `infra/terraform/modules/foundations/app/variables.tf`
- Modify: `infra/terraform/modules/foundations/app/main.tf`
- Modify: `infra/terraform/components/platform/main.tf`
- Modify: `infra/terraform/components/app/main.tf`
- Test: `infra/terraform/modules/foundations/sandbox_platform/tests/sandbox_platform.tftest.hcl`
- Test: `infra/terraform/modules/foundations/app/tests/app.tftest.hcl`

**Interfaces:**
- Produces: Firestore database and runtime IAM, GCS lifecycle rules for `media/` and `exports/`, Cloud Run quota environment variables, API concurrency 4/max instances 3, and web max instances 2.

- [ ] **Step 1: Add failing Terraform tests.** Assert Firestore exists, runtime has datastore access, state is untouched, media expires after one day, exports after three days, and exact runtime environment/scaling values are planned.
- [ ] **Step 2: Run targeted `terraform test`.** Expect failures because resources and variables are absent.
- [ ] **Step 3: Implement the smallest Terraform changes.** Enable Firestore API, create Native-mode database only in the sandbox platform, grant least-privilege runtime access, and parameterize Cloud Run concurrency/scaling.
- [ ] **Step 4: Implement lifecycle rules.** Apply prefix-scoped deletion only to the application media bucket.
- [ ] **Step 5: Pass merged JSON values through component roots.** Convert numeric values to strings only at the Cloud Run environment boundary.
- [ ] **Step 6: Re-run targeted Terraform tests and formatting.** Expect pass.

### Task 4: Cloud Armor rate limiting

**Files:**
- Modify: `infra/terraform/modules/foundations/public_edge/variables.tf`
- Modify: `infra/terraform/modules/foundations/public_edge/main.tf`
- Modify: `infra/terraform/modules/foundations/public_edge/outputs.tf`
- Modify: `infra/terraform/components/public-edge/main.tf`
- Test: `infra/terraform/modules/foundations/public_edge/tests/public_edge.tftest.hcl`

**Interfaces:**
- Consumes: `rate_limits` JSON.
- Produces: one security policy attached to both backends, preview-safe explicit priorities, HTTP 429 exceed actions, per-IP keys, and configured ban duration.

- [ ] **Step 1: Add failing plan assertions.** Prove both backends reference one policy and the public/API/film rules preserve precedence.
- [ ] **Step 2: Run `terraform test`.** Expect output/resource failures.
- [ ] **Step 3: Add policy and rules.** Use public catch-all 120/minute, API 30/minute, and render/song 5/10 minutes, each keyed by IP with a 3600-second ban where supported.
- [ ] **Step 4: Pass JSON values from the root and expose non-sensitive evidence outputs.**
- [ ] **Step 5: Re-run Terraform tests and formatting.** Expect pass.

### Task 5: CI, billing runbook, and full verification

**Files:**
- Modify: `.github/workflows/tests.yaml`
- Modify: `.github/workflows/terraform.yml`
- Modify: `docs/operations/USAGE_COST_CONTROLS.md`
- Test: `infra/terraform/tools/config-validator/test/validate-config.test.mjs`

**Interfaces:**
- Produces: CI proof that configuration, API behavior, Terraform plans/tests, formatting, lint/build, and security checks stay green.

- [ ] **Step 1: Add a failing static workflow test if schema validation is not already mandatory on both test and Terraform paths.**
- [ ] **Step 2: Wire only missing CI gates.** Reuse existing actions; do not duplicate jobs.
- [ ] **Step 3: Document billing controls.** Record the A$200 project alert budget, A$150 Vertex AI / Agent Platform spend-cap target, A$35 Cloud Run spend-cap target, A$250 tolerance, Preview/latency caveat, ClickHouse exclusion, and evidence commands/screenshots required before claiming active protection.
- [ ] **Step 4: Run fresh full verification.** API pytest, web tests/build, config validator, Terraform fmt/validate/tests, TFLint where available, Trivy/config checks, and `git diff --check` must pass.
- [ ] **Step 5: Commit, push, open PR, wait for CI, request independent review, and merge only after every check is green.** Keep ST-45 In Progress until production apply and observable quota/rate/retention evidence exist.
