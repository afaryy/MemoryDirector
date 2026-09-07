import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("production web image", () => {
  it("copies public assets into the runtime image", () => {
    const dockerfile = readFileSync(resolve(process.cwd(), "Dockerfile"), "utf8");

    expect(dockerfile).toMatch(
      /COPY\s+--from=build\s+\/app\/public\s+\.\/public/,
    );
  });
});
