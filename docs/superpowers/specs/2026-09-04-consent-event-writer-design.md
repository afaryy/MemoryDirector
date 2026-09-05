# Consent Event Writer Design

**Status:** proposed

## Purpose

ClickHouse is Memory Director's durable, queryable evidence layer for approved
media use and export outcomes. The existing `mcp-clickhouse` service must remain
read-only: it is used by the API to verify evidence immediately before rendering
and immediately before returning an export. A separate internal writer records
the minimal facts required for that verification.

## Components and trust boundaries

```text
Browser → API → private consent-event writer → ClickHouse
              ↘ read-only authenticated MCP → ClickHouse
```

- The browser uploads selected media to private Cloud Storage through the API
  flow. It never receives ClickHouse credentials or a writer URL.
- The API sends the writer only `media_id`, `event_type`, a request/session ID,
  and non-sensitive timing/decision facts. It never sends media bytes, Cloud
  Storage URIs, browser file paths, generated audio, or user-entered narration.
- The consent-event writer is a private Cloud Run service. It accepts only the
  API runtime service account, validates a small allowlist of event types, and
  inserts events using a dedicated ClickHouse writer identity.
- `mcp-clickhouse` stays private and read-only. It uses the existing
  `memory_director_mcp` reader identity and checks the evidence without writing
  or receiving secrets from the browser.

## Data contract

Use the existing `production_events` table. The writer accepts only:

```json
{
  "session_id": "request-scoped identifier",
  "media_id": "opaque media hash",
  "event_type": "media_selected | media_held_back | render_started | export_completed | export_failed",
  "render_id": "optional opaque render identifier"
}
```

The writer fills `occurred_at` using ClickHouse's existing server default. It
does not accept user IDs, captions, titles, location, device metadata, or raw
media. Invalid event types and empty identifiers are rejected. Events are
append-only; the writer has no SELECT, UPDATE, ALTER, DROP, or user-management
permissions.

The exporter records `media_selected` after the user explicitly selects an
already analysed asset. Before render and before archive return, the API uses
the existing authenticated MCP reader to require one selected event for every
requested media ID. The writer records `render_started` only after the first
gate passes, `export_completed` only after the second gate passes, and
`export_failed` for recoverable post-gate errors. A missing writer, unavailable
MCP, malformed result, or absent selection evidence denies export; no ZIP is
returned.

## Credentials and Terraform ownership

The ClickHouse bootstrap automation creates two separate users:

- `memory_director_mcp`: read-only role, used only by mcp-clickhouse;
- `memory_director_event_writer`: INSERT-only role on
  `memory_director.production_events`, used only by the writer.

The generated writer connection JSON lives in a separate Secret Manager secret
named `clickhouse-event-writer-credentials`; it is not combined with the MCP
reader secret. Terraform creates the secret container and grants only the
writer Cloud Run service account `secretAccessor`. The API's runtime identity
gets `run.invoker` on the writer, and no ClickHouse writer secret. GitHub
Actions accesses migration credentials only in its protected ClickHouse
bootstrap workflow.

The platform component owns the writer service and its IAM; the app component
receives only the private writer URI as a non-secret environment variable.
All Cloud Run services use internal invocation and workload identity. No
service-account key is created.

## Failure, retention, and rollout

Writer failures do not undo a user's private source media or selection record.
They return a retryable API error when a selection cannot be evidenced. Export
fails closed if the corresponding event does not exist. No raw media is copied
to ClickHouse.

Roll out in two phases: first provision the writer identity, secret container,
internal service, schema grants, and API configuration; then enable production
event recording and perform a consented-demo smoke run. Keep hosted ClickHouse
evidence marked pending until that actual run verifies both gate calls and an
export. The normal sandbox destroy can remove writer runtime resources but must
retain the bootstrap state and identity layers according to the existing
bootstrap policy.

## Tests and acceptance criteria

- Unit tests prove event validation and that the writer constructs INSERT-only
  statements with no raw-media fields.
- API tests prove selection causes exactly one writer request, a writer failure
  prevents export, and the MCP guardian sees the event evidence at both stages.
- Terraform tests/validation prove the API can invoke the writer, the writer
  alone reads the writer secret, and MCP remains configured with write access
  disabled.
- A consented-demo smoke test records selected media, verifies the two
  read-only MCP checks, and returns a playable export without exposing secrets
  or personal media.
