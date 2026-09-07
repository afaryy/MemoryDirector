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
  assert.deepEqual(config.agent_engine, {
    enabled: true,
    location: "australia-southeast2",
    model_location: "australia-southeast1",
    runtime_service_account_email:
      "memory-director-agent@memory-director-505708.iam.gserviceaccount.com",
    staging_bucket_name: "memory-director-505708-agent-staging",
  });
});

test("rejects an Agent Engine identity outside the configured project", () => {
  const result = spawnSync("node", [fileURLToPath(validator), "--json", JSON.stringify({
    project_id: "memory-director-505708",
    agent_engine: {
      enabled: true,
      runtime_service_account_email: "memory-director-agent@another-project.iam.gserviceaccount.com",
      staging_bucket_name: "memory-director-505708-agent-staging",
    },
  })], { encoding: "utf8" });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /runtime_service_account_email/);
});

test("rejects an unsupported Agent Engine location", () => {
  const result = spawnSync("node", [fileURLToPath(validator), "--json", JSON.stringify({
    project_id: "memory-director-505708",
    agent_engine: {
      enabled: true,
      location: "australia-southeast1",
      runtime_service_account_email:
        "memory-director-agent@memory-director-505708.iam.gserviceaccount.com",
      staging_bucket_name: "memory-director-505708-agent-staging",
    },
  })], { encoding: "utf8" });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /agent_engine\/location/);
});

test("rejects an unsupported Gemini model location", () => {
  const result = spawnSync("node", [fileURLToPath(validator), "--json", JSON.stringify({
    project_id: "memory-director-505708",
    agent_engine: {
      enabled: true,
      location: "australia-southeast2",
      model_location: "australia-southeast2",
      runtime_service_account_email:
        "memory-director-agent@memory-director-505708.iam.gserviceaccount.com",
      staging_bucket_name: "memory-director-505708-agent-staging",
    },
  })], { encoding: "utf8" });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /agent_engine\/model_location/);
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

test("accepts the approved four-layer control configuration", () => {
  const result = spawnSync("node", [
    fileURLToPath(validator),
    fileURLToPath(new URL("common-environment.json", configDir)),
    fileURLToPath(new URL("memory-director.json", configDir)),
    fileURLToPath(new URL("sandbox.json", configDir)),
  ], { encoding: "utf8" });

  assert.equal(result.status, 0, result.stderr);
  const common = JSON.parse(readFileSync(new URL("common-environment.json", configDir), "utf8"));
  const project = JSON.parse(readFileSync(new URL("memory-director.json", configDir), "utf8"));
  const sandbox = JSON.parse(readFileSync(new URL("sandbox.json", configDir), "utf8"));
  assert.deepEqual(common.application_limits, {
    max_film_duration_seconds: 60,
    max_media_items: 15,
    media_analysis_max_attempts: 2,
    max_upload_file_mb: 250,
    max_request_text_chars: 2000,
    global_daily_film_hard_max: 100,
  });
  assert.equal(sandbox.quotas.global_daily_film_limit, 30);
  assert.equal(project.budgets.monthly_cost_tolerance, 200);
});

test("rejects a sandbox daily film limit above the approved hard maximum", () => {
  const result = spawnSync("node", [fileURLToPath(validator), "--json", JSON.stringify({
    environment: "sandbox",
    quotas: {
      visitor_daily_film_limit: 5,
      ip_daily_film_limit: 10,
      ip_max_concurrent_films: 2,
      global_daily_film_limit: 101,
      global_max_concurrent_films: 6,
      visitor_daily_original_song_limit: 3,
      global_daily_original_song_limit: 20,
    },
  })], { encoding: "utf8" });

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /global_daily_film_limit/);
});

test("rejects a monthly cost tolerance above USD 200", () => {
  const result = spawnSync("node", [fileURLToPath(validator), "--json", JSON.stringify({
    project_id: "memory-director-505708",
    budgets: {
      currency: "USD",
      monthly_cost_tolerance: 201,
      project_alert_budget: 150,
      vertex_ai_spend_cap: 110,
      cloud_run_spend_cap: 25,
    },
  })], { encoding: "utf8" });

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /monthly_cost_tolerance/);
});

test("rejects retention configuration that targets Terraform state", () => {
  const result = spawnSync("node", [fileURLToPath(validator), "--json", JSON.stringify({
    retention: {
      upload_days: 1,
      export_days: 3,
      terraform_state_days: 3,
    },
  })], { encoding: "utf8" });

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /terraform_state_days/);
});
