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

The official server defaults to read-only queries. Keep `CLICKHOUSE_ALLOW_WRITE_ACCESS=false` and `CLICKHOUSE_ALLOW_DROP=false`.

## Verification script

1. Apply `infra/clickhouse/001_schema.sql` and `002_demo_data.sql` to a consented demo database.
2. Start `mcp-clickhouse` with the Cloud connection environment variables.
3. Have the production agent call `run_query` with the generated query for `demo-user` and `travel`.
4. Record the tool name, a hash of the SQL, returned row count, and the user-facing explanation in the demo recording. Do not record credentials or raw personal media.
