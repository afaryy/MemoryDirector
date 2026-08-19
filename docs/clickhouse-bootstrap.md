# ClickHouse sandbox bootstrap

The ClickHouse database user and schema are managed by the manual `ClickHouse`
GitHub Actions workflow. Terraform creates only Secret Manager containers and
their IAM bindings; it never stores a secret value in Terraform state.

## One-time migration secret

After the platform component has been applied, create a version in the
`clickhouse-migration-credentials` secret in the GCP project that owns the
ClickHouse connection. The JSON value must contain:

```json
{
  "CLICKHOUSE_HOST": "hostname-only.clickhouse.cloud",
  "CLICKHOUSE_PORT": "8443",
  "CLICKHOUSE_DATABASE": "memory_director",
  "CLICKHOUSE_USER": "default",
  "CLICKHOUSE_PASSWORD": "temporary-migration-password"
}
```

This is a migration-only credential. It is not mounted into API or MCP Cloud
Run services. Do not commit it or paste it into an issue or pull request.

## Run bootstrap

In GitHub Actions, run `ClickHouse` with:

- `operation=bootstrap`
- `secret_project_id=memory-director-505708` (or the project that owns the secrets)
- `migration_secret_name=clickhouse-migration-credentials`
- `runtime_secret_name=clickhouse-credentials`
- `confirm=CLICKHOUSE_SANDBOX`

The workflow generates a random password and bearer token, creates the
`memory_director_reader` role and `memory_director_mcp` user, applies
`infra/clickhouse/001_schema.sql` and `002_demo_data.sql`, then writes the
runtime JSON to a new Secret Manager version. It never prints credential
values.

The Terraform MCP service is intentionally gated behind
`terraform.yml`'s `enable_mcp=true` input. Apply it only after this bootstrap
has written the runtime JSON; the Cloud Run service reads the latest secret
version and exposes the official server at `<Cloud Run URI>/mcp`. The service
is private: callers need Cloud Run invocation permission and the generated
MCP bearer token.

The current platform configuration targets the existing `staylong` GCP project
for Cloud Run and its runtime service account, while
`mcp_secret_project_id=memory-director-505708` keeps the ClickHouse runtime
secret in the GCP project whose display name is `memory-director`. Before enabling MCP, the GitHub
Actions deployer must be allowed to read/add versions in that project, and the
platform apply must be allowed to grant the runtime identity cross-project
Secret Manager access. The Cloud Run reference uses the full
`projects/memory-director-505708/secrets/clickhouse-credentials` resource name.

The human administrator who bootstraps WIF must grant the Terraform deployer
permission to manage these two secrets in `memory-director-505708` (prefer a narrow
custom role; `roles/secretmanager.secretAdmin` is the broad fallback). The
workflow identity needs to read the migration secret and add a new runtime
secret version. The platform apply grants the Cloud Run runtime service
account `roles/secretmanager.secretAccessor` on the cross-project runtime
secret.

If your organization does not permit cross-project IAM, set
`mcp_secret_project_id` to the platform project and create the secret there
instead. Do not copy secret values into Terraform or GitHub.

## Verify

Run the same workflow with `operation=verify`. It reads the latest runtime
secret and executes a read-only count query against `creative_preferences`.

After the private Cloud Run service is applied, run it again with
`operation=smoke` and `mcp_endpoint=<Cloud Run URI>`. The workflow obtains a
short-lived Cloud Run identity token, sends the generated MCP bearer token in
the application `Authorization` header, initializes the Streamable HTTP MCP
session, and calls `run_query` for the same preference count. It does not print
the response body or either credential.
