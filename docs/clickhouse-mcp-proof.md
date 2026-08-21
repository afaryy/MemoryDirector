# ClickHouse MCP runtime proof

## Required runtime behaviour

Memory Director must connect to the official `mcp-clickhouse` server and invoke its `run_query` tool at runtime. The query retrieves only accepted music preferences for the current user and occasion, then the agent explains the recommendation in plain language.

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
3. Open the Web flow, create a plan, and confirm that the API calls `run_query` with the generated query for `demo-user` and `travel`.
4. Record the tool name, a hash of the SQL, returned row count, and the user-facing explanation in the demo recording. Do not record credentials or raw personal media.
