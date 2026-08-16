# Terraform bootstrap and state lifecycle

## Purpose

`bootstrap-state` creates the long-lived, private GCS backend used by all
subsequent Memory Director Terraform roots. It is deliberately not a normal
sandbox component and has no GitHub Actions destroy path.

The implementation has three Terraform layers:

1. `infra/terraform/modules/base/gcs_state_bucket`: one hardened state bucket.
2. `infra/terraform/modules/foundations/bootstrap_state`: enables Cloud Storage
   API and composes the base bucket module.
3. `infra/terraform/projects/memory-director/sandbox/bootstrap-state`: the only
   root that supplies Memory Director sandbox values.

## Initial local bootstrap

Run these commands only as a human GCP administrator. Authenticate with
Application Default Credentials first; do not create a service-account key.

```bash
gcloud auth application-default login
cd infra/terraform/projects/memory-director/sandbox/bootstrap-state
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars and choose a globally unique bucket name.
terraform init -backend=false
terraform fmt -check -recursive
terraform validate
terraform plan
terraform apply
```

The first `init -backend=false` intentionally keeps state local because the
remote bucket does not exist yet. The administrator needs permission to enable
`storage.googleapis.com` and create/manage the state bucket in the selected
project.

## Migrate bootstrap state to GCS

After the initial apply succeeds, copy `backend.hcl.example` to `backend.hcl`,
replace the bucket placeholder with the created bucket name, then migrate state:

```bash
cp backend.hcl.example backend.hcl
terraform init -migrate-state -backend-config=backend.hcl
terraform state list
```

`backend.hcl` is local operational configuration and must not contain secrets.
It is excluded by `.gitignore` because it contains the installation-specific
bucket name. All later Terraform roots receive their backend configuration from
the same long-lived GCS bucket.

## Normal sandbox cleanup

Only `sandbox-platform` and `sandbox-app` will expose a GitHub Actions destroy
operation. They must require the exact confirmation value
`DESTROY_SANDBOX`. The state backend and GitHub WIF identity remain in place so
the sandbox can be applied again.

## Break-glass retirement

Do not run `terraform destroy` on this root. To retire the project completely:

1. Destroy the sandbox application and platform first.
2. Export the remote Terraform state to an approved encrypted location.
3. As a human GCP administrator, tear down WIF, Terraform service accounts and
   their IAM bindings using the separate `bootstrap-identity` procedure.
4. Remove the state bucket last, outside any Terraform root that still uses it
   as its backend.

The state bucket has `prevent_destroy` enabled as a safety guard. Removing it
requires an intentional, reviewed code change during break-glass retirement.

## Bootstrap GitHub identity

After state migration, a human GCP administrator can initialize and apply
`infra/terraform/projects/memory-director/sandbox/bootstrap-identity` with the
same backend bucket, using a `backend.hcl` whose prefix is
`memory-director/sandbox/bootstrap-identity`.

This root enables the IAM, IAM Credentials and Security Token Service APIs,
creates the GitHub Actions workload identity pool and provider, and creates the
`github-terraform-sandbox` service account. The provider accepts only tokens
for `afaryy/MemoryDirector`, `refs/heads/main`, and the GitHub `sandbox`
environment. It has no service-account key.

The deployment identity receives explicit platform-provisioning roles rather
than Editor or Owner. Review those roles before the first apply; later platform
work can reduce or split them further. Do not add a GitHub workflow destroy
operation for this identity root.
