# Application deployment

The application deploy workflow builds immutable API and web images, pushes
them to the Artifact Registry repository named by
`projects/config/memory-director.json`, and updates Cloud Run with Terraform.
It never uses a long-lived service-account key: GitHub Actions authenticates
through the bootstrap WIF provider and the sandbox Terraform service account.

## Triggers

- A successful `CI` workflow run on `main` deploys `all`.
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

The workflow reads the project ID, region, Artifact Registry repository name,
and Terraform state bucket from the checked-in non-sensitive JSON
configuration. Secrets such as Gemini credentials remain in Secret Manager
and are not image build arguments.

## Safe manual operations

Use `terraform.yml` for validate, plan, apply, or destroy of `platform` or
`app`. Bootstrap roots are intentionally excluded. A sandbox destroy requires
the exact confirmation string `DESTROY_SANDBOX` and must be performed only
after confirming that application data is disposable.
