import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

type Rgb = [number, number, number];

const css = readFileSync(resolve(process.cwd(), "src/app/globals.css"), "utf8");

function variable(name: string): Rgb {
  const value = css.match(new RegExp(`--${name}:\\s*(#[0-9a-f]{6})`, "i"))?.[1];
  if (!value) throw new Error(`Missing --${name} color`);

  return [1, 3, 5].map((index) => Number.parseInt(value.slice(index, index + 2), 16)) as Rgb;
}

function luminance(color: Rgb): number {
  const [red, green, blue] = color.map((channel) => {
    const value = channel / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });

  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrast(foreground: Rgb, background: Rgb): number {
  const lighter = Math.max(luminance(foreground), luminance(background));
  const darker = Math.min(luminance(foreground), luminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

describe("secondary text contrast regression", () => {
  // Regression: ISSUE-001 — normal-sized secondary text failed WCAG AA contrast.
  // Found by /qa on 2026-09-07.
  it("keeps palette text colors at 4.5:1 or better on their light backgrounds", () => {
    expect(contrast(variable("muted"), variable("sand"))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(variable("muted"), variable("paper"))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(variable("terracotta"), [255, 255, 255])).toBeGreaterThanOrEqual(4.5);
    expect(contrast(variable("moss"), variable("sand"))).toBeGreaterThanOrEqual(4.5);
  });

  it("uses the compliant muted color for the request placeholder", () => {
    expect(css).toMatch(/\.wizard__request textarea::placeholder\s*{[^}]*color:\s*var\(--muted\)/);
  });

  it("keeps the preview badge background dark enough for sand text", () => {
    expect(css).toMatch(/\.wizard__preview-badge\s*{[^}]*background:\s*rgba\(0,\s*0,\s*0,\s*\.15\)/);
  });
});
