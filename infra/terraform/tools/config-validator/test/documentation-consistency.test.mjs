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

function readDocument(path) {
  return readFileSync(resolve(repositoryRoot, path), "utf8");
}

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

test("each current journey document rejects the obsolete combined action", () => {
  for (const path of [
    "README.md",
    "docs/ABOUT.md",
    "docs/PROJECT_BRIEF.md",
    "docs/ARCHITECTURE.md",
    "docs/ux/MOBILE_PRODUCTION_FLOW.md",
    "docs/demo/DEMO_RUNBOOK.md",
    "docs/submission/DEVPOST_PROJECT_PAGE.md",
  ]) {
    assert.doesNotMatch(readDocument(path), /Save\s*&\s*share/i, path);
  }
});

test("product and UX documents match the public call path and controls", () => {
  const readme = readDocument("README.md");
  assert.doesNotMatch(readme, /hackathon/i);
  assert.match(readme, /docs\/CAPABILITY_EVIDENCE\.md/);
  assert.match(readme, /memorydirector\.com/);

  const brief = readDocument("docs/PROJECT_BRIEF.md");
  for (const [label, claim] of [
    ["direct Gemini storyboard", /direct Gemini storyboard/],
    ["does not call Agent Engine", /does not\s+call\s+that\s+endpoint/],
    ["ST-52", /ST-52/],
    ["ST-9", /ST-9/],
    ["ST-17", /ST-17/],
  ]) {
    assert.match(brief, claim, `docs/PROJECT_BRIEF.md: ${label}`);
  }

  const mobileFlow = readDocument("docs/ux/MOBILE_PRODUCTION_FLOW.md");
  for (const label of ["Clear all", "Make again", "Save video", "Share video", "server-generated JPEG"]) {
    assert.match(mobileFlow, new RegExp(label), `docs/ux/MOBILE_PRODUCTION_FLOW.md: ${label}`);
  }
});

test("architecture and operations distinguish the public Web and Agent Engine paths", () => {
  const architecture = readDocument("docs/ARCHITECTURE.md");
  for (const boundary of ["/storyboards", "/production-proposals", "not called by the current Web UI", "shared `demo-user`"]) {
    assert.match(architecture, new RegExp(boundary), `docs/ARCHITECTURE.md: ${boundary}`);
  }

  const agentEngine = readDocument("docs/operations/AGENT_ENGINE.md");
  assert.match(agentEngine, /34024861486/);

  const deployment = readDocument("docs/operations/APP_DEPLOYMENT.md");
  for (const evidence of ["34188276089", "34188310631", "https://memorydirector.com/", "https://memorydirector.com/api/health"]) {
    assert.match(deployment, new RegExp(evidence.replaceAll("/", "\\/")), evidence);
  }
  assert.doesNotMatch(deployment, /32362975036/);
  assert.doesNotMatch(deployment, /https:\/\/memory-director-[^)`\s]+\.run\.app/);

  const publicEdge = readDocument("docs/operations/public-edge.md");
  assert.match(publicEdge, /direct `\.run\.app` requests return HTTP\s+404 by design/);

  const clickHouseProof = readDocument("docs/clickhouse-mcp-proof.md");
  assert.match(clickHouseProof, /Web UI uses\s+`\/storyboards`, not `\/production-proposals`/);
  assert.match(clickHouseProof, /separate runtime evidence/);
});

test("QA documents record the completed physical iPhone scope", () => {
  const physicalQaPath = resolve(repositoryRoot, "docs/qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md");
  assert.equal(existsSync(physicalQaPath), true, "ST-52 physical iPhone report must exist");
  const physicalQa = readFileSync(physicalQaPath, "utf8");
  for (const evidence of [
    "iPhone 11",
    "iOS 26.6.1",
    "Chrome (version not recorded)",
    "6b738f4",
    "34188276089",
    "34188310631",
  ]) {
    assert.ok(physicalQa.includes(evidence), evidence);
  }
  assert.doesNotMatch(physicalQa, /\| (?:Fail|Pending) \|/);

  const browserQa = readDocument("docs/qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md");
  assert.match(browserQa, /ST-52-PHYSICAL-IPHONE-ACCEPTANCE\.md/);
  assert.doesNotMatch(browserQa, /Do not mark ST-52 Done/);

  const accessibility = readDocument("docs/qa/ST-31-visual-accessibility-regression.md");
  assert.match(accessibility, /fixed, merged, deployed, and verified/);
  assert.match(accessibility, /ST-31 is Done/);
  assert.match(accessibility, /iPhone 11/);
  assert.doesNotMatch(accessibility, /Remaining before ST-31 can be Done/);
});

test("current evidence distinguishes main from the deployed Web release", () => {
  for (const path of [
    "docs/CAPABILITY_EVIDENCE.md",
    "docs/submission/EVIDENCE_PACKAGE.md",
  ]) {
    assert.match(readDocument(path), /eab585c/, `${path}: current main commit`);
  }

  for (const path of [
    "docs/CAPABILITY_EVIDENCE.md",
    "docs/operations/APP_DEPLOYMENT.md",
    "docs/submission/EVIDENCE_PACKAGE.md",
    "design-qa.md",
  ]) {
    const document = readDocument(path);
    assert.match(document, /6b738f4/, `${path}: final release commit`);
    assert.doesNotMatch(document, /64ee654|cc6c102|34132016535|34132225436/, `${path}: stale release evidence`);
  }
});

test("public evidence package preserves recorded release gates", () => {

  const evidencePackage = readDocument("docs/submission/EVIDENCE_PACKAGE.md");
  assert.match(evidencePackage, /VIDEO_URL_REQUIRED/);
  assert.match(evidencePackage, /- \[x\] Rights register is complete/);
  assert.match(evidencePackage, /Rights approval[\s\S]*Ready/);
  assert.match(evidencePackage, /Devpost entry[\s\S]*Pending/);
});
