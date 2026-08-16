import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const validator = new URL("../validate-config.mjs", import.meta.url);
const configDir = new URL("../../../projects/config/", import.meta.url);

test("accepts the checked-in non-sensitive project and environment configuration", () => {
  const result = spawnSync("node", [fileURLToPath(validator), fileURLToPath(new URL("memory-director.json", configDir)), fileURLToPath(new URL("sandbox.json", configDir))], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
});

test("rejects configuration with an unknown property", () => {
  const result = spawnSync("node", [fileURLToPath(validator), "--json", '{"project_id":"staylong","unexpected_secret":"nope"}'], { encoding: "utf8" });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unexpected_secret/);
});
