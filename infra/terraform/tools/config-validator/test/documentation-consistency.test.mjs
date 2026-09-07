import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const repositoryRoot = fileURLToPath(new URL("../../../../../", import.meta.url));

function markdownFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) {
      return entry.name === "superpowers" ? [] : markdownFiles(path);
    }
    return entry.isFile() && entry.name.endsWith(".md") ? [path] : [];
  });
}

const activeDocuments = [
  resolve(repositoryRoot, "README.md"),
  resolve(repositoryRoot, "design-qa.md"),
  ...markdownFiles(resolve(repositoryRoot, "docs")),
];

function localLinkTarget(rawTarget) {
  const target = rawTarget.trim().replace(/^<|>$/g, "").split(/\s+[\"']/)[0];
  if (!target || target.startsWith("#") || /^[a-z][a-z0-9+.-]*:/i.test(target)) return null;
  return decodeURIComponent(target.split("#")[0]);
}

function brokenLocalLinks(documents) {
  return documents.flatMap((document) => {
    const markdown = readFileSync(document, "utf8");
    const targets = [...markdown.matchAll(/!?\[[^\]]*\]\(([^)]+)\)/g)]
      .map((match) => localLinkTarget(match[1]))
      .filter(Boolean);

    return targets.flatMap((target) => {
      const resolved = resolve(dirname(document), target);
      return existsSync(resolved)
        ? []
        : [`${relative(repositoryRoot, document)} -> ${target}`];
    });
  });
}

test("active documentation has valid local links", () => {
  assert.deepEqual(brokenLocalLinks(activeDocuments), []);
});

test("the capability matrix separates evidence levels", () => {
  const matrixPath = resolve(repositoryRoot, "docs/CAPABILITY_EVIDENCE.md");
  assert.equal(existsSync(matrixPath), true, "docs/CAPABILITY_EVIDENCE.md must exist");
  const matrix = readFileSync(matrixPath, "utf8");

  for (const heading of ["Implemented", "Deployed", "Physical device", "Final submission"]) {
    assert.match(matrix, new RegExp(`\\b${heading}\\b`));
  }
});

test("current journey documents use the deployed action labels and evidence boundary", () => {
  const currentJourneyDocuments = [
    "README.md",
    "docs/ABOUT.md",
    "docs/PROJECT_BRIEF.md",
    "docs/ARCHITECTURE.md",
    "docs/ux/MOBILE_PRODUCTION_FLOW.md",
    "docs/demo/DEMO_RUNBOOK.md",
    "docs/submission/DEVPOST_PROJECT_PAGE.md",
    "docs/submission/DEMO_SCRIPT.md",
  ].map((path) => readFileSync(resolve(repositoryRoot, path), "utf8"));
  const currentJourney = currentJourneyDocuments.join("\n");

  assert.doesNotMatch(currentJourney, /Save\s*&\s*share/i);
  assert.match(currentJourney, /Save video/);
  assert.match(currentJourney, /Share video/);
  assert.match(currentJourney, /ST-52/);
  assert.match(currentJourney, /memorydirector\.com/);
});
