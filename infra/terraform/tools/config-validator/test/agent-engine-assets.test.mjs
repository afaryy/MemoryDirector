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
  assert.match(workflow, /smoke_agent_engine\.py/);
  assert.match(workflow, /MEMORY_FILM_PLANNER_RESOURCE/);
  assert.match(workflow, /192915586401/);
  assert.match(workflow, /terraform[^\n]*apply/);
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
