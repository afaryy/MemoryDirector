import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { metadata } from "./layout";

describe("RootLayout metadata", () => {
  it("publishes the Memory Director icon for browser tabs", () => {
    expect(metadata.icons).toEqual({
      icon: [{ type: "image/svg+xml", url: "/icon.svg" }],
    });
  });

  it("ships a valid, recognizable brand icon at the published URL", () => {
    const icon = readFileSync(resolve(process.cwd(), "public/icon.svg"), "utf8");
    const document = new DOMParser().parseFromString(icon, "image/svg+xml");

    expect(document.querySelector("parsererror")).toBeNull();
    expect(document.documentElement.getAttribute("viewBox")).toBe("0 0 64 64");
    expect(document.querySelector("rect")?.getAttribute("fill")).toBe("#606c38");
    expect(document.querySelector("g")?.getAttribute("stroke")).toBe("#fff");
  });
});
