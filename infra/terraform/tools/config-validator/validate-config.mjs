import { readFileSync } from "node:fs";
import Ajv2020 from "ajv/dist/2020.js";

const schema = JSON.parse(readFileSync(new URL("../../projects/config/config.schema.json", import.meta.url)));
const ajv = new Ajv2020({ allErrors: true, strict: true });
const validate = ajv.compile(schema);
const argumentsToValidate = process.argv.slice(2);
const values = argumentsToValidate[0] === "--json"
  ? [JSON.parse(argumentsToValidate[1])]
  : argumentsToValidate.map((path) => JSON.parse(readFileSync(path, "utf8")));

if (values.length === 0) {
  process.stderr.write("Provide one or more JSON configuration files, or --json <value>.\n");
  process.exit(2);
}

const errors = values.flatMap((value) => {
  const schemaErrors = validate(value) ? [] : validate.errors ?? [];
  const agentEngineErrors = [];
  if (value.project_id && value.agent_engine) {
    const expectedEmail = `memory-director-agent@${value.project_id}.iam.gserviceaccount.com`;
    if (value.agent_engine.runtime_service_account_email !== expectedEmail) {
      agentEngineErrors.push({
        instancePath: "/agent_engine/runtime_service_account_email",
        message: `must equal ${expectedEmail}`,
      });
    }
    const expectedBucket = `${value.project_id}-agent-staging`;
    if (value.agent_engine.staging_bucket_name !== expectedBucket) {
      agentEngineErrors.push({
        instancePath: "/agent_engine/staging_bucket_name",
        message: `must equal ${expectedBucket}`,
      });
    }
  }
  return [...schemaErrors, ...agentEngineErrors];
});
if (errors.length > 0) {
  const message = errors.map((error) => {
    const property = error.params?.additionalProperty ? ` (${error.params.additionalProperty})` : "";
    return `${error.instancePath || "data"} ${error.message}${property}`;
  }).join("\n");
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

process.stdout.write(`Validated ${values.length} non-sensitive configuration file(s).\n`);
