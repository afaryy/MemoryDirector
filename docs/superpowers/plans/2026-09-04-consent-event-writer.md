# Consent Event Writer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record minimal, anonymous selection/export evidence in ClickHouse through a private writer while preserving the existing MCP reader as read-only.

**Architecture:** A dedicated FastAPI writer accepts authenticated internal Cloud Run requests from the API and inserts only allowlisted event fields with a dedicated INSERT-only ClickHouse identity. The API records selections and outcomes; its existing MCP guardian queries the same table twice before an export is returned. Terraform owns the Cloud Run service, identity, secret references, and invoker IAM.

**Tech Stack:** Python 3.12, FastAPI, clickhouse-connect, pytest/httpx, Cloud Run, Secret Manager, Terraform, GitHub Actions, existing mcp-clickhouse.

**Spec:** `docs/superpowers/specs/2026-09-04-consent-event-writer-design.md`

## Global Constraints

- Never send media bytes, `gs://` URIs, browser paths, captions, narration, generated audio, passwords, or tokens to ClickHouse.
- The writer accepts only `media_selected`, `media_held_back`, `render_started`, `export_completed`, and `export_failed` event types.
- The writer identity may INSERT into `memory_director.production_events` only; MCP remains read-only with `CLICKHOUSE_ALLOW_WRITE_ACCESS=false`.
- The API receives no writer database password; it invokes the private writer using its Cloud Run identity.
- Missing writer/MCP evidence fails the export closed; selected private media stays intact.

### Task 1: Add the validated event-writer application

**Files:**
- Create: `services/consent-writer/app/main.py`
- Create: `services/consent-writer/app/events.py`
- Create: `services/consent-writer/tests/test_events.py`
- Create: `services/consent-writer/pyproject.toml`

**Interfaces:**
- Produces `POST /events` accepting `{session_id, media_id, event_type, render_id?}`.
- Produces `ClickHouseEventRepository.record(event: ConsentEvent) -> None`.

- [ ] **Step 1: Write the failing validation test.**
  ```python
  def test_event_rejects_disallowed_type_and_raw_media_fields():
      with pytest.raises(ValueError):
          ConsentEvent(session_id="s", media_id="m", event_type="delete_media")
  ```
- [ ] **Step 2: Run it.** `cd services/consent-writer && uv run pytest tests/test_events.py -q` — expect import failure.
- [ ] **Step 3: Implement `ConsentEvent` and repository.** Validate opaque IDs, the exact event allowlist, and optional render ID. Execute a parameterized `INSERT INTO production_events (session_id, media_id, event_type, render_id) VALUES` with no user-supplied SQL. Expose a FastAPI endpoint returning 201 only after repository success.
- [ ] **Step 4: Verify.** `cd services/consent-writer && uv run pytest -q` — expect PASS.
- [ ] **Step 5: Commit.** `git add services/consent-writer && git commit -m "feat(ST-36): add consent event writer"`

### Task 2: Create the restricted ClickHouse writer identity and secret contract

**Files:**
- Modify: `infra/clickhouse/bootstrap.py`
- Modify: `infra/clickhouse/tests/test_bootstrap.py`
- Modify: `.github/workflows/clickhouse.yml`
- Modify: `infra/terraform/modules/foundations/sandbox_platform/main.tf`

**Interfaces:**
- Produces `memory_director_event_writer` with `INSERT` only on `production_events`.
- Produces separate Secret Manager container `clickhouse-event-writer-credentials`.

- [ ] **Step 1: Write failing bootstrap assertions.** Assert generated SQL contains `GRANT INSERT ON memory_director.production_events`, contains no SELECT/ALTER/DROP grant, and credentials JSON is separate from the reader payload.
- [ ] **Step 2: Run.** `cd infra/clickhouse && uv run pytest tests/test_bootstrap.py -q` — expect fail.
- [ ] **Step 3: Implement writer SQL and workflow generation.** Add `render_writer_identity_sql`; generate a new random writer password in the protected bootstrap workflow; add it only to the writer secret version. Do not output or log it.
- [ ] **Step 4: Add Terraform secret container.** Include the writer secret ID but grant `secretAccessor` only to the writer service account created in Task 3.
- [ ] **Step 5: Verify and commit.** Run bootstrap tests, then `git commit -m "infra(ST-36): provision event writer credentials"`.

### Task 3: Provision private writer runtime with least privilege

**Files:**
- Create: `infra/terraform/modules/foundations/consent_event_writer/main.tf`
- Create: `infra/terraform/modules/foundations/consent_event_writer/variables.tf`
- Create: `infra/terraform/modules/foundations/consent_event_writer/outputs.tf`
- Modify: `infra/terraform/modules/foundations/sandbox_platform/main.tf`
- Modify: `infra/terraform/modules/foundations/sandbox_platform/outputs.tf`
- Modify: `infra/terraform/components/platform/main.tf`

**Interfaces:**
- Produces private URI output `consent_event_writer_uri`.
- Consumes API runtime SA email and writer-secret reference.

- [ ] **Step 1: Write Terraform static tests.** Assert writer uses a different service account than API, only API runtime appears in its `run.invoker` binding, and writer secret IAM excludes API/MCP identities.
- [ ] **Step 2: Run.** `terraform -chdir=infra/terraform/components/platform validate` — expect fail until module is wired.
- [ ] **Step 3: Implement module.** Use existing `base/service_account` and `base/cloud_run_service`; create an internal-only service named `${resource_name}-consent-events`, service-specific secret accessor binding, and invoker binding for API runtime only. Export URI.
- [ ] **Step 4: Verify.** Run JSON config validator, `terraform fmt -check -recursive infra/terraform`, and platform validate.
- [ ] **Step 5: Commit.** `git commit -m "infra(ST-36): provision private consent writer"`.

### Task 4: Record events from API and retain read-only export gating

**Files:**
- Create: `services/api/app/consent_events.py`
- Create: `services/api/tests/test_consent_events.py`
- Modify: `services/api/app/main.py`
- Modify: `services/api/tests/test_media_render_endpoint.py`
- Modify: `infra/terraform/modules/foundations/app/main.tf`

**Interfaces:**
- Produces `ConsentEventPublisher.publish(event: ConsentEvent) -> None` using authenticated Cloud Run HTTP.
- Consumes `CONSENT_EVENT_WRITER_ENDPOINT` and runtime identity.

- [ ] **Step 1: Write failing endpoint tests.** Assert an accepted selected decision produces one `media_selected` event; publisher failure returns 502 and does not claim a persisted selection; a successful export records `render_started` before rendering and `export_completed` only after the second MCP gate.
- [ ] **Step 2: Run.** `cd services/api && uv run pytest tests/test_consent_events.py tests/test_media_render_endpoint.py -q` — expect fail.
- [ ] **Step 3: Implement publisher.** Build a short-timeout Cloud Run identity-token client; send only IDs and allowlisted event types. Resolve configuration from environment. Wire `decide_media` and `/renders/export`; keep direct-upload compatibility path free of fabricated ClickHouse evidence.
- [ ] **Step 4: Wire only the URI into app Terraform.** Add the non-secret private writer URI to API environment variables and API runtime as writer invoker. Do not add a writer secret to API.
- [ ] **Step 5: Verify and commit.** Run API tests then `git commit -m "feat(ST-36): record consent export events"`.

### Task 5: Validate, document, and prepare a PR without fabricated hosted evidence

**Files:**
- Create: `docs/operations/consent-event-writer.md`
- Modify: `.github/workflows/tests.yaml`

- [ ] **Step 1: Add tests workflow coverage.** Run the consent-writer unit suite, API suite, Terraform format/validate, and configuration schema validation.
- [ ] **Step 2: Document smoke evidence.** Specify provision → bootstrap schema/identities → choose consented demo media → inspect two MCP gates → inspect sanitized writer log/event count → download export. Label it pending until performed.
- [ ] **Step 3: Run local validation.**
  ```bash
  cd services/consent-writer && uv run pytest -q
  cd ../api && uv run pytest -q
  terraform fmt -check -recursive infra/terraform
  ```
- [ ] **Step 4: Commit and PR.** `git commit -m "test(ST-36): validate consent evidence workflow"`; push `feat/ST-36-automatic-film-renderer`; open a PR with actual test output only. Keep ST-36 In Progress until Cloud evidence is recorded.
