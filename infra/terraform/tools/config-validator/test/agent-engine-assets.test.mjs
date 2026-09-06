import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const repositoryRoot = new URL("../../../../../", import.meta.url);

test("Agent Engine deployment is manual, WIF-authenticated, and smoke-gated", () => {
  const workflow = readFileSync(
    new URL(".github/workflows/deploy-agent-engine.yml", repositoryRoot),
    "utf8",
  );

  assert.match(workflow, /workflow_dispatch:/);
  assert.match(workflow, /DEPLOY_AGENT_SANDBOX/);
  assert.match(workflow, /environment: sandbox/);
  assert.match(workflow, /google-github-actions\/auth@v2/);
  assert.match(workflow, /scripts\.smoke_agent_engine/);
  assert.match(workflow, /MEMORY_FILM_PLANNER_RESOURCE/);
  assert.match(workflow, /192915586401/);
  assert.match(workflow, /terraform[^\n]*apply/);
  assert.match(workflow, /python -m scripts\.deploy_agent_engine/);
  assert.match(workflow, /python -m scripts\.smoke_agent_engine/);
  assert.match(workflow, /agent_location="\$\(jq -er '\.agent_engine\.location'/);
  assert.match(workflow, /model_location="\$\(jq -er '\.agent_engine\.model_location'/);
  assert.match(
    workflow,
    /GOOGLE_CLOUD_LOCATION: \$\{\{ steps\.config\.outputs\.agent_location \}\}/,
  );
  assert.match(
    workflow,
    /AGENT_ENGINE_MODEL_LOCATION: \$\{\{ steps\.config\.outputs\.model_location \}\}/,
  );
  assert.doesNotMatch(
    workflow,
    /GOOGLE_CLOUD_LOCATION: \$\{\{ steps\.config\.outputs\.region \}\}/,
  );
  assert.doesNotMatch(workflow, /python scripts\/(?:deploy|smoke)_agent_engine\.py/);
  assert.doesNotMatch(workflow, /secrets versions access/);
});

test("normal app deployments preserve the currently active Agent Engine resource", () => {
  const workflow = readFileSync(
    new URL(".github/workflows/deploy.yml", repositoryRoot),
    "utf8",
  );

  assert.match(workflow, /MEMORY_FILM_PLANNER_RESOURCE/);
  assert.match(workflow, /agent_engine_resource/);

  const terraformWorkflow = readFileSync(
    new URL(".github/workflows/terraform.yml", repositoryRoot),
    "utf8",
  );
  assert.match(terraformWorkflow, /MEMORY_FILM_PLANNER_RESOURCE/);
  assert.match(terraformWorkflow, /agent_engine_resource/);

  const publicDomainWorkflow = readFileSync(
    new URL(".github/workflows/public-domain-control.yml", repositoryRoot),
    "utf8",
  );
  assert.match(publicDomainWorkflow, /MEMORY_FILM_PLANNER_RESOURCE/);
  assert.match(publicDomainWorkflow, /agent_engine_resource/);
});
