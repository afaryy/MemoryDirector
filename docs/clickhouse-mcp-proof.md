# ClickHouse MCP runtime proof

## Required runtime behaviour

Memory Director connects to the official `mcp-clickhouse` server and invokes its
`run_query` tool at runtime in two bounded paths. The export guardian reads the
selected-media consent state and can block rendering. Separately, the Agent Engine
production-proposal endpoint retrieves an accepted seeded demonstration preference
and returns an explanation in its typed proposal. The current public Web UI uses
`/storyboards`, not `/production-proposals`, and displays neither a tool log nor a
preference explanation.

## Cloud configuration

Store these values in Secret Manager or the deployment environment, never in the browser or Git repository:

- `CLICKHOUSE_HOST`
- `CLICKHOUSE_USER` — a least-privilege, read-only service account
- `CLICKHOUSE_PASSWORD`
- `CLICKHOUSE_DATABASE`
- `CLICKHOUSE_SECURE=true`
- For HTTP/SSE MCP transport: `CLICKHOUSE_MCP_AUTH_TOKEN` or an OAuth/OIDC FastMCP configuration

The API receives the private MCP Cloud Run URI as `CLICKHOUSE_MCP_ENDPOINT` and the
same JSON credential payload through the `CLICKHOUSE_CREDENTIALS_JSON` Secret
Manager reference. The API obtains a Cloud Run identity token with its runtime
service account; no token is sent to the browser. Terraform wires both values when
the app workflow is run with the platform `mcp_uri` output.

The official server defaults to read-only queries. Keep `CLICKHOUSE_ALLOW_WRITE_ACCESS=false` and `CLICKHOUSE_ALLOW_DROP=false`.

## Verification script

1. Apply `infra/clickhouse/001_schema.sql` and `002_demo_data.sql` to a consented demo database.
2. Start `mcp-clickhouse` with the Cloud connection environment variables.
3. Run the guarded Agent Engine deployment smoke and confirm it produces a valid
   production proposal with `preference_tool_invoked: true` for the synthetic
   fixture.
4. Run a consented Web export and verify the separate guardian query succeeds; also
   exercise its fail-closed result with a non-sensitive test fixture.
5. Record only the workflow URL, tool name, hashed query identifier, row count, and
   pass/fail result. Present this as separate runtime evidence, not an in-app panel.
   Do not record credentials, raw database responses, or personal media.
