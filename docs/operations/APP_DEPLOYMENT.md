# Application deployment

The application deploy workflow builds immutable API and web images, pushes
them to the Artifact Registry repository named by
`projects/config/memory-director.json`, and updates Cloud Run with Terraform.
It never uses a long-lived service-account key: GitHub Actions authenticates
through the bootstrap WIF provider and the sandbox Terraform service account.

## Triggers

- A successful `Tests` workflow run on `main` deploys `all` only when the
  sandbox `AUTO_DEPLOY_ENABLED` variable is `true`.
- `Actions > Deploy application > Run workflow` supports `api`, `web`, or
  `all`.

The workflow uses separate remote-state prefixes for `app-api` and `app-web`.
For an `all` deployment it applies the API first, reads the resulting Cloud
Run URL, bakes that URL into the web image, and then applies the web service.
This keeps a selective API or web deployment from deleting the other service.

## Required sandbox variables

Configure these GitHub **Environment** variables in the `sandbox` environment
after bootstrap has been applied:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `TERRAFORM_SERVICE_ACCOUNT`
- `GCP_PROJECT_ID` (must be `memory-director-505708`)
- `AUTO_DEPLOY_ENABLED` (`false` until automatic deployment is intentionally enabled)

The workflow reads the project ID, region, Artifact Registry repository name,
and Terraform state bucket from the checked-in non-sensitive JSON
configuration. Secrets such as Gemini credentials remain in Secret Manager
and are not image build arguments.

The API uses Google Cloud Vertex AI with its Cloud Run service account by
default. `GEMINI_API_KEY` is not required for the deployed path; it is only an
optional local developer-API override. The Vertex model location defaults to
`us-central1` and can be changed with `GEMINI_LOCATION`.

The API also receives these non-secret settings from the Terraform app
component:

- `GOOGLE_CLOUD_PROJECT`: the configured GCP project ID;
- `GOOGLE_CLOUD_LOCATION`: the configured sandbox region;
- `MEDIA_BUCKET`: the private platform bucket named `<project_id>-media`;
- `GEMINI_MODEL`: optional model override, defaulting to `gemini-2.5-flash`.
- `LYRIA_LOCATION`: optional Lyria 3 location override, defaulting to `global`.

The original-memory-song path uses the same Cloud Run service account and
Vertex AI authentication path as the deployed Gemini planner. It does not
require a browser-visible API key. Lyria 3 remains a preview model.

## Original-song hosted smoke evidence

On 2026-09-03, the production export endpoint was verified with a generated
one-pixel PNG and generic garden-memory text only. The request selected
`original_song`; the returned ZIP passed integrity testing and contained an
MP4, JPG cover, and TXT caption. Local container metadata inspection confirmed
an exact 60-second MP4 with H.264 video and an AAC audio track.

This verifies the deployed API render path, including generated-audio mixing.
Later ST-49 browser evidence verifies the original-song and no-music Web
journeys. Neither result is a production guarantee for a preview model or proof
of the final submission recording.

`POST /media/analyze` requires `consent=true`, accepts only image/video MIME
types, and uses the deployed configuration's 250 MiB per-file ceiling. It stores originals privately and returns
schema-validated metadata without exposing a GCS URI. A selected or held-back
decision never deletes the original. Use a non-sensitive fixture for hosted
verification; do not place real personal media in CI.

## Safe manual operations

Use `terraform.yml` for validate, plan, apply, or destroy of `platform` or
`app`. Bootstrap roots are intentionally excluded. A sandbox destroy requires
the exact confirmation string `DESTROY_SANDBOX` and must be performed only
after confirming that application data is disposable.

## Hosted sandbox verification

The public application is <https://memorydirector.com/>. The current audited Web
release is commit `64ee654a999549322dbeea22f9ffc2b8b29acdaf`, deployed by workflow
run [34132225436](https://github.com/afaryy/MemoryDirector/actions/runs/34132225436).
That manual web-only run authenticated with GitHub OIDC/WIF, built the immutable
image, and updated the existing Cloud Run Web service through its isolated state.
The same commit passed the complete Tests workflow in run
[34132016535](https://github.com/afaryy/MemoryDirector/actions/runs/34132016535).

The run was verified with a non-sensitive fixture:

- API health: `200` from `https://memorydirector.com/api/health`.
- Web home: `200` from `https://memorydirector.com/`.
- Approved export: `200` from `POST /renders/export`; the returned ZIP contained one MP4, one JPG
  cover, and one TXT caption, and passed `unzip -t`.

After public-edge lockdown, direct `.run.app` origins are not public verification
URLs; HTTP 404 there is expected. Operators can restore direct ingress through the
documented rollback if the public edge fails.

Do not treat a synthetic fixture result as approval to upload personal media.
Hosted media analysis still requires explicit consent, and final demo media must
be recorded in the rights register.
