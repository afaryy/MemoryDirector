import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const validator = new URL("../validate-config.mjs", import.meta.url);
const configDir = new URL("../../../projects/config/", import.meta.url);

test("accepts the checked-in non-sensitive project and environment configuration", () => {
  const result = spawnSync("node", [fileURLToPath(validator), fileURLToPath(new URL("memory-director.json", configDir)), fileURLToPath(new URL("sandbox.json", configDir))], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
});

test("binds Memory Director deployments to the approved GCP project", () => {
  const config = JSON.parse(readFileSync(new URL("memory-director.json", configDir), "utf8"));

  assert.equal(config.project_id, "memory-director-505708");
  assert.equal(config.project_number, "192915586401");
  assert.equal(
    config.mcp_invoker_service_account_email,
    "github-terraform-sandbox@memory-director-505708.iam.gserviceaccount.com",
  );
});

test("rejects configuration with an unknown property", () => {
  const result = spawnSync("node", [fileURLToPath(validator), "--json", '{"project_id":"example-project","unexpected_secret":"nope"}'], { encoding: "utf8" });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unexpected_secret/);
});

test("accepts a complete non-sensitive public-edge configuration", () => {
  const result = spawnSync("node", [fileURLToPath(validator), "--json", JSON.stringify({
    project_id: "example-project",
    public_edge: {
      apex_domain: "memorydirector.com",
      cloudflare_zone_id: "d963f645b3ea1a7b68611369f90cc276",
      api_path_prefix: "/api",
    },
  })], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
});

test("rejects an invalid public-edge API path prefix", () => {
  const result = spawnSync("node", [fileURLToPath(validator), "--json", JSON.stringify({
    project_id: "example-project",
    public_edge: {
      apex_domain: "memorydirector.com",
      cloudflare_zone_id: "d963f645b3ea1a7b68611369f90cc276",
      api_path_prefix: "api",
    },
  })], { encoding: "utf8" });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /api_path_prefix/);
});
