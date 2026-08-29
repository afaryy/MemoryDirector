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
