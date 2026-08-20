# ST-13 Media Analysis and Safe Rendering Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (required for inline execution) to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Add a consent-gated, private-GCS-backed Vertex AI Gemini media analysis endpoint whose validated result can be selected or held without deleting the original and can feed the existing deterministic renderer.

**Architecture:** Keep the HTTP layer independent from Google Cloud through MediaStorage and MediaAnalyzer protocols. Production adapters use the existing Cloud Run runtime identity, private GCS media bucket, and Vertex AI Gemini structured output; tests use in-memory fakes. Add a small process-local decision registry for explicit non-destructive selection; durable curation remains represented by the existing production proposal contract.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, Google Gen AI SDK, google-cloud-storage, pytest, httpx, uv.

**Spec:** docs/superpowers/specs/2026-08-20-st13-media-analysis-design.md

## Global Constraints

- Consent must be exactly true; otherwise return 409 before reading the upload.
- Accept only image or video MIME types and enforce a 50 MiB upload limit.
- Originals remain private and are never deleted by analysis or selection.
- media_id is content-derived from SHA-256 and retries reuse the same ID.
- Gemini output is untrusted and must be validated against a strict Pydantic schema with allow-listed enums.
- API responses never expose gs:// URIs, bucket names, credentials, or raw provider responses.
- No real personal media or live cloud credentials are used in PR tests.
- Bootstrap Terraform resources remain outside this application change and daily destroy workflow.
- Branch remains media/ST-13-rendering-pipeline; Linear ST-13 stays In Progress until hosted evidence exists.

---

### Task 0: Synchronize the implementation branch with origin/main

**Files:**
- Modify: Git history only; preserve the approved design spec.

**Interfaces:**
- Consumes: latest origin/main.
- Produces: current application and Terraform baseline in media/ST-13-rendering-pipeline.

- [ ] Step 1: Verify worktree and remote state.

    Run:
    git status --short --branch
    git fetch origin main
    git diff --name-status HEAD origin/main

    Expected: only the approved spec is unique to this branch; no user changes are discarded.

- [ ] Step 2: Merge latest main without destructive commands.

    Run:
    git merge --no-edit origin/main

    Expected: merge completes cleanly. If a conflict occurs, preserve both latest main changes and the approved spec.

- [ ] Step 3: Verify the synchronized baseline.

    Run:
    pytest -q services/api/tests

    Expected: existing API tests pass.

- [ ] Step 4: Push the synchronized baseline if a merge was created.

    Run:
    git push origin media/ST-13-rendering-pipeline

### Task 1: Define media storage and analysis contracts with failing tests

**Files:**
- Create: services/api/app/media_analysis.py
- Create: services/api/app/media_storage.py
- Create: services/api/tests/test_media_analysis.py
- Create: services/api/tests/test_media_storage.py

**Interfaces:**
- Consumes: existing FastAPI/Pydantic conventions.
- Produces: StoredMedia, MediaAnalysis, MediaStorage, MediaAnalyzer, MediaDecisionState, and media_id_for_bytes.

- [ ] Step 1: Write failing contract tests.

    Test identical bytes produce the same media_id, different bytes produce a different sha256-prefixed ID, invalid quality/orientation are rejected by MediaAnalysis, and InMemoryMediaStorage returns hash, size, MIME type, and private gs:// URI without exposing any delete operation.

    Run:
    cd services/api && uv run pytest tests/test_media_analysis.py tests/test_media_storage.py -q

    Expected: FAIL because the new modules and types do not exist.

- [ ] Step 2: Implement the minimal contracts.

    Use a Pydantic StoredMedia model with media_id, content_type, size_bytes, sha256, and gs_uri. Use a strict MediaAnalysis model with extra="forbid", bounded description, quality_score in [0,1], duplicate_of, allow-listed privacy_flags (contains_face, contains_text, possible_sensitive_document), orientation (portrait, landscape, square, unknown), and optional non-negative duration_seconds.

    Implement media_id_for_bytes with hashlib.sha256 and return f"sha256:{full_digest}". Implement InMemoryMediaStorage.put with content-addressed keys and no delete method. Implement GcsMediaStorage with the same put contract and a lazy google.cloud.storage import.

- [ ] Step 3: Run focused tests green.

    Run:
    cd services/api && uv run pytest tests/test_media_analysis.py tests/test_media_storage.py -q

    Expected: PASS without cloud credentials.

- [ ] Step 4: Commit the contract slice.

    Run:
    git add services/api/app/media_analysis.py services/api/app/media_storage.py services/api/tests/test_media_analysis.py services/api/tests/test_media_storage.py
    git commit -m "feat(ST-13): add media analysis and storage contracts"

### Task 2: Add the Vertex AI Gemini analyzer adapter with failing tests

**Files:**
- Modify: services/api/app/media_analysis.py
- Create: services/api/tests/test_gemini_media_analyzer.py
- Modify: services/api/pyproject.toml
- Modify: services/api/uv.lock

**Interfaces:**
- Consumes: StoredMedia and existing Vertex environment settings.
- Produces: VertexGeminiMediaAnalyzer.analyze(stored_media) -> MediaAnalysis.

- [ ] Step 1: Write the failing adapter test.

    Build a fake Gen AI client that records models.generate_content arguments and returns valid JSON. Assert the request contains the private URI, validated MIME type, application/json response MIME type, and MediaAnalysis schema; assert the returned model contains no gs_uri.

    Run:
    cd services/api && uv run pytest tests/test_gemini_media_analyzer.py -q

    Expected: FAIL because the adapter is not implemented.

- [ ] Step 2: Add the dependency and minimal adapter.

    Add google-cloud-storage>=2.18,<3.0 and run uv lock. The default constructor follows the existing Vertex identity path when GEMINI_API_KEY is absent. Build contents as [prompt, types.Part.from_uri(file_uri=stored_media.gs_uri, mime_type=stored_media.content_type)], set response_mime_type="application/json", set response_schema=MediaAnalysis, parse response.text, and convert provider/schema exceptions into a private MediaAnalysisError without URI or response-body text.

- [ ] Step 3: Run adapter and existing Gemini tests.

    Run:
    cd services/api && uv run pytest tests/test_gemini_media_analyzer.py tests/test_gemini_client.py -q

    Expected: PASS.

- [ ] Step 4: Commit the adapter slice.

    Run:
    git add services/api/app/media_analysis.py services/api/tests/test_gemini_media_analyzer.py services/api/pyproject.toml services/api/uv.lock
    git commit -m "feat(ST-13): add Vertex Gemini media analyzer"

### Task 3: Add consent-gated analysis and non-destructive decision endpoints

**Files:**
- Modify: services/api/app/main.py
- Create: services/api/tests/test_media_endpoint.py

**Interfaces:**
- Consumes: MediaStorage, MediaAnalyzer, MediaAnalysis, media_id_for_bytes, and StoredMedia.
- Produces: POST /media/analyze and POST /media/{media_id}/decision.

- [ ] Step 1: Write failing API tests.

    Cover: consent=false returns 409 and storage.put is never called; valid image/video with fake storage/analyzer returns 201 and schema fields without gs://; unsupported MIME returns 415; body over 50 MiB returns 413; analyzer failure returns 502; invalid model output is rejected; repeated selected/held decisions are idempotent and never call delete.

    Run:
    cd services/api && uv run pytest tests/test_media_endpoint.py -q

    Expected: FAIL because routes and providers do not exist.

- [ ] Step 2: Implement dependency providers and upload validation.

    Add get_media_storage returning GcsMediaStorage.from_environment and get_media_analyzer returning VertexGeminiMediaAnalyzer.from_environment. Missing configuration maps to generic 503. In /media/analyze, check consent before read, validate MIME, read MAX_UPLOAD_BYTES + 1, compute media_id, store, analyze, register unselected, and return only the public MediaAnalysis response. Map storage/model failures to generic 502.

- [ ] Step 3: Implement the decision registry and endpoint.

    Add a process-local MediaDecisionRegistry with set(media_id, status in selected|held_back, reason) and get(media_id). The registry changes only metadata and has no delete operation. POST /media/{media_id}/decision accepts status and reason, returns the same state for repeated identical requests, and returns 404 for unknown IDs. Analysis registers every successful ID as unselected.

- [ ] Step 4: Run focused and existing API tests.

    Run:
    cd services/api && uv run pytest tests/test_media_endpoint.py tests/test_export_endpoint.py tests/test_production.py -q

    Expected: PASS; existing export and curation behavior is unchanged.

- [ ] Step 5: Commit the endpoint slice.

    Run:
    git add services/api/app/main.py services/api/app/media_analysis.py services/api/tests/test_media_endpoint.py
    git commit -m "feat(ST-13): add consented media analysis endpoint"

### Task 4: Add configuration documentation and privacy regression tests

**Files:**
- Modify: docs/ARCHITECTURE.md
- Modify: docs/operations/APP_DEPLOYMENT.md
- Create: services/api/tests/test_media_privacy.py

**Interfaces:**
- Consumes: completed API contract and Terraform runtime settings.
- Produces: operator documentation and regression tests for privacy boundaries.

- [ ] Step 1: Write failing privacy tests.

    Assert analysis responses do not contain gs://, MEDIA_BUCKET, model API key names, or raw provider responses, and that held-back decisions leave fake stored objects present.

    Run:
    cd services/api && uv run pytest tests/test_media_privacy.py -q

    Expected: FAIL until the response fixtures and assertions are wired.

- [ ] Step 2: Implement the public response safeguard.

    Return only media_id, description, quality_score, duplicate_of, privacy_flags, orientation, duration_seconds, and decision status. Never serialize StoredMedia directly. Log only media ID, content type, size, and outcome on provider failures.

- [ ] Step 3: Document runtime configuration.

    Document MEDIA_BUCKET, GEMINI_MODEL, GOOGLE_CLOUD_PROJECT, and GOOGLE_CLOUD_LOCATION as non-secret Cloud Run settings. State that Terraform supplies private-bucket object access and Vertex AI access to the runtime service account, and bootstrap is not part of daily application deploy/destroy.

- [ ] Step 4: Run privacy and full API tests.

    Run:
    cd services/api && uv run pytest -q

    Expected: PASS with no secrets or private URIs in captured responses.

- [ ] Step 5: Commit safeguards.

    Run:
    git add docs/ARCHITECTURE.md docs/operations/APP_DEPLOYMENT.md services/api/tests/test_media_privacy.py
    git commit -m "docs(ST-13): document media privacy boundary"

### Task 5: Run repository checks, open PR evidence, and update Linear

**Files:**
- Modify: none unless a check exposes an implementation defect.

**Interfaces:**
- Consumes: implementation commits and existing GitHub Actions workflows.
- Produces: passing checks, a PR with ST-13 evidence, and an In Progress Linear update.

- [ ] Step 1: Run application checks.

    Run:
    cd services/api && uv run pytest -q
    cd ../.. && npm --prefix apps/web test -- --run

    Expected: all API and web tests pass.

- [ ] Step 2: Run repository infrastructure and security checks.

    Run the commands used by .github/workflows/tests.yaml, .github/workflows/terraform.yml, and Trivy. Do not apply or destroy Terraform in this PR.

    Expected: JSON/schema validation, Terraform format/validate/tests, application tests, and Trivy pass.

- [ ] Step 3: Push and open the PR.

    Push media/ST-13-rendering-pipeline. The PR description must state consent and 50 MiB/MIME validation, private GCS originals, Vertex AI structured analysis, no source deletion, no URI/credential exposure, test commands/results, and that hosted sandbox verification remains required before ST-13 can be Done.

- [ ] Step 4: Update Linear without falsely completing ST-13.

    Add a comment linking the PR and test evidence. Keep ST-13 In Progress until an authorized sandbox smoke test proves multimodal analysis plus MP4/cover/caption export.

- [ ] Step 5: Record hosted verification separately.

    After PR merge and authorized deployment, run a non-sensitive fixture smoke test, attach sanitized evidence to ST-13, and verify the response has no gs:// URI or secret before considering completion.

## Self-review checklist

- [x] Every spec requirement has a task.
- [x] Production interfaces are named before later tasks consume them.
- [x] No task depends on bootstrap destroy or secrets in source control.
- [x] Tests are written before each implementation slice and include the expected failing command.
- [x] No TODO, TBD, or unspecified "handle errors" placeholders remain.

