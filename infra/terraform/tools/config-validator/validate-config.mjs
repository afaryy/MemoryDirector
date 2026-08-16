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

const errors = values.flatMap((value) => validate(value) ? [] : validate.errors ?? []);
if (errors.length > 0) {
  const message = errors.map((error) => {
    const property = error.params?.additionalProperty ? ` (${error.params.additionalProperty})` : "";
    return `${error.instancePath || "data"} ${error.message}${property}`;
  }).join("\n");
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

process.stdout.write(`Validated ${values.length} non-sensitive configuration file(s).\n`);
