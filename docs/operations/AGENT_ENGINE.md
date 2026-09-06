# Agent Engine operations

Memory Director deploys one bounded ADK `memory_film_planner` to Vertex AI
Agent Engine. It creates a typed, exactly 60-second production plan; it does
not render, export, publish, delete media, or receive credentials from the
browser.

## Runtime boundary

- Google Gemini is the only model provider.
- `memory-director-agent@memory-director-505708.iam.gserviceaccount.com` is the
  no-key runtime identity. Terraform grants it Vertex AI use, access to the
  `clickhouse-credentials` secret container, and invocation of the private
  `memory-director-sandbox-mcp` Cloud Run service.
- The Vertex AI service agent can mint this identity's short-lived tokens.
- The ADK agent exposes one tool:
  `lookup_approved_music_preference`. That wrapper sends a fixed read-only
  query through the official `mcp-clickhouse` server; neither the browser nor
  Gemini can supply arbitrary SQL.
- The deployment object contains a Secret Manager version name, never a secret
  value. The runtime reads the MCP bearer token and obtains a short-lived Cloud
  Run identity token only when the tool runs.
- The API validates known media IDs, rejects private `gs://` references and
  requires selected segments to total exactly 60 seconds before accepting a
  plan. The response schema is included in the instruction and enforced by the
  API instead of ADK `output_schema`: Google documents that combining
  `output_schema` and tools is not reliable for Gemini 2.5. Export remains
  behind the separate approval and Consent Guardian gate.

Reference: [ADK structured input and output](https://adk.dev/agents/llm-agents/#structure-data-input-and-output)
and [Vertex AI Agent Engine deployment](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/deploy).

## Deploy

The deployment workflow is manual and runs only from `main` in the protected
`sandbox` GitHub environment:

1. Open **Actions → Deploy Agent Engine → Run workflow**.
2. Choose `deploy` and enter `DEPLOY_AGENT_SANDBOX`.
3. The workflow checks the exact GCP project, preserves the current API image,
   ingress mode, MCP service and optional consent writer, then applies only the
   platform additions needed by Agent Engine.
4. It deploys the locked ADK package with zero minimum instances.
5. A synthetic request must produce a schema-valid 60-second plan and contain
   the approved preference-tool invocation. If this fails, the API is not
   changed.
6. Only after the smoke test passes does Terraform set
   `MEMORY_FILM_PLANNER_RESOURCE` on the API.

The sanitized artifact contains a resource name, selected fixture media IDs,
duration, music direction and two booleans. It contains no photo, private URI,
database response, bearer token or Secret Manager value.

## Roll back

Every successful run writes the previous and active Agent Engine resource
names to the GitHub step summary. To roll back:

1. Run the same workflow with `operation=rollback`.
2. Paste the previous full `projects/.../reasoningEngines/...` name into
   `rollback_resource` and enter `DEPLOY_AGENT_SANDBOX`.
3. The earlier resource must pass the same live smoke test before Terraform
   points the API back to it.

The workflow intentionally provides no Agent Engine or bootstrap destroy. A
failed new deployment never replaces the working API resource. Remove an
unused Agent Engine separately only after rollback evidence and cost review;
never delete the currently configured resource.

## Evidence gate

Local tests prove schemas, adapters, IAM plans and workflow guards. They do not
prove a hosted Agent Engine call. Hosted claims require all of the following
from a successful manual workflow run:

- the immutable Git commit and workflow URL;
- the Agent Engine resource name and runtime smoke artifact;
- `agent_engine_runtime: true`;
- `preference_tool_invoked: true`;
- `selected_duration_seconds: 60`;
- a subsequent API request using that configured resource;
- no credentials, personal media or private GCS URI in logs or artifacts.

Until that run succeeds, submission copy must describe Agent Engine as
implemented and deployment-ready, not hosted or verified.
