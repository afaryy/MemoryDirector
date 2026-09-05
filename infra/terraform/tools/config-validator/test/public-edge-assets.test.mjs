import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const repositoryRoot = new URL("../../../../../", import.meta.url);

test("public-domain workflow requires guarded operations and runtime-only Cloudflare credentials", () => {
  const workflow = readFileSync(new URL(".github/workflows/public-domain-control.yml", repositoryRoot), "utf8");

  assert.match(workflow, /options: \[provision, lockdown, destroy\]/);
  assert.match(workflow, /DESTROY_PUBLIC_EDGE/);
  assert.match(workflow, /CLOUDFLARE_API_TOKEN/);
  assert.match(workflow, /environment: sandbox/);
});

test("public-edge operations documentation covers rollout and rollback", () => {
  const operations = readFileSync(new URL("docs\/operations\/public-edge.md", repositoryRoot), "utf8");

  for (const requiredText of ["public-domain-control.yml", "provision", "lockdown", "DESTROY_PUBLIC_EDGE", "CLOUDFLARE_API_TOKEN"]) {
    assert.match(operations, new RegExp(requiredText));
  }
});

test("serverless NEG backends do not set unsupported backend timeouts", () => {
  const module = readFileSync(new URL("infra/terraform/modules/foundations/public_edge/main.tf", repositoryRoot), "utf8");
  assert.doesNotMatch(module, /resource "google_compute_backend_service" "(?:api|web)" \{[\s\S]*?timeout_sec/);
});

test("lockdown reads the deployed Cloud Run images instead of absent Terraform state outputs", () => {
  const workflow = readFileSync(new URL(".github/workflows/public-domain-control.yml", repositoryRoot), "utf8");
  assert.match(workflow, /gcloud run services describe "\$\{\{ steps\.config\.outputs\.resource_name \}\}-api".*--format='value\(spec\.template\.spec\.containers\[0\]\.image\)'/s);
  assert.match(workflow, /gcloud run services describe "\$\{\{ steps\.config\.outputs\.resource_name \}\}-web".*--format='value\(spec\.template\.spec\.containers\[0\]\.image\)'/s);
  assert.match(workflow, /test -n "\$api_image"/);
  assert.match(workflow, /test -n "\$web_image"/);
  assert.match(workflow, /test -n "\$mcp_endpoint"/);
  assert.doesNotMatch(workflow, /terraform -chdir=infra\/terraform\/components\/app output -raw (?:api_image|web_image)/);
});

test("deployment serializes with lockdown and preserves the existing ingress mode", () => {
  const deploy = readFileSync(new URL(".github/workflows/deploy.yml", repositoryRoot), "utf8");
  const publicDomain = readFileSync(new URL(".github/workflows/public-domain-control.yml", repositoryRoot), "utf8");

  assert.match(deploy, /concurrency:\n  group: deploy-sandbox/);
  assert.match(publicDomain, /concurrency:\n  group: deploy-sandbox/);
  assert.match(deploy, /id: ingress/);
  assert.match(deploy, /for service in api web; do/);
  assert.match(deploy, /gcloud run services describe "\$\{\{ steps\.config\.outputs\.resource_name \}\}-\$service"/);
  assert.match(deploy, /NOT_FOUND/);
  assert.doesNotMatch(deploy, /2>\/dev\/null \|\| true/);
  assert.match(deploy, /-var="public_ingress=\$\{\{ steps\.ingress\.outputs\.public_ingress \}\}"/);
});

test("automatic deployment is disabled until the approved GCP target is explicitly enabled", () => {
  const deploy = readFileSync(new URL(".github/workflows/deploy.yml", repositoryRoot), "utf8");

  assert.match(deploy, /vars\.GCP_PROJECT_ID == 'memory-director-505708'/);
  assert.match(deploy, /vars\.AUTO_DEPLOY_ENABLED == 'true'/);
});
