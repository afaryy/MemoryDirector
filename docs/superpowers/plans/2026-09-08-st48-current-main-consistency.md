# ST-48 Current-Main Documentation Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every active product, architecture, operations, UX, demo, and submission document agree with merged commit `64ee654`, verified production evidence, and current Linear completion boundaries.

**Architecture:** Add one evidence matrix as the claim source of truth and one Node test that validates active Markdown links and known cross-document invariants. Update documents by audience while keeping implementation, deployed browser, physical-device, and final-submission evidence distinct.

**Tech Stack:** Markdown, Node.js built-in test runner, existing Terraform config-validator test suite, GitHub Actions evidence, Linear issue status.

**Spec:** [Linear ST-48](https://linear.app/yvonney/issue/ST-48/reconcile-current-main-code-architecture-and-submission-documentation)

## Global Constraints

- Use `https://memorydirector.com/` as the public product URL.
- Direct Cloud Run URLs are internal recovery details, not judge-facing links after ingress lockdown.
- Do not claim full phone-library access, direct social posting, a completed three-minute video, completed physical-device QA, or instantaneous billing guarantees.
- Treat ST-17 and ST-9 as In Progress and ST-52 as Todo until their own evidence is complete.
- Treat ST-31, ST-37, ST-42, ST-43, ST-45, ST-46, and ST-49 as completed only for their recorded scopes.
- Do not add secrets, private media, fabricated evidence, or the word “hackathon” to `README.md`.
- Historical specifications and implementation plans under `docs/superpowers/` remain historical records and are not rewritten as current product documentation.

---

### Task 1: Establish the claim source of truth

**Files:**
- Create: `docs/CAPABILITY_EVIDENCE.md`
- Create: `infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

**Interfaces:**
- Consumes: source files, existing tests, production QA reports, workflow runs `34024861486`, `34118291595`, `34132016535`, and `34132225436`, plus current Linear statuses.
- Produces: a matrix with `Implemented`, `Deployed`, `Physical device`, and `Final submission` evidence columns; reusable active-document link validation.

- [ ] **Step 1: Write the failing documentation test**

Create a Node test that defines the active-document list, extracts local Markdown links, strips fragments, resolves each path relative to its source document, and reports every missing target. Add an assertion that `docs/CAPABILITY_EVIDENCE.md` exists and contains the four evidence-level headings.

```js
test("active documentation has valid local links", () => {
  const failures = collectBrokenLocalLinks(activeDocuments);
  assert.deepEqual(failures, []);
});

test("the capability matrix separates evidence levels", () => {
  const matrix = readFileSync(new URL("docs/CAPABILITY_EVIDENCE.md", repositoryRoot), "utf8");
  for (const heading of ["Implemented", "Deployed", "Physical device", "Final submission"]) {
    assert.match(matrix, new RegExp(`\\b${heading}\\b`));
  }
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `node --test infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

Expected: failure because `docs/CAPABILITY_EVIDENCE.md` does not exist.

- [ ] **Step 3: Create the capability evidence matrix**

Cover public routing, deliberate media selection, append/duplicate/Clear all, reorder, voice fallback, consent, three soundtrack choices, Agent Engine planning, ClickHouse MCP preference and export gates, 60-second render, preview/cover/playback, Make again, separate Save and Share, accessibility, usage/cost controls, physical-device QA, rights approval, final video, and Devpost submission. Each row must cite a source/test/workflow/QA report or an explicit Linear issue.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `node --test infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

Expected: all documentation-consistency tests pass.

- [ ] **Step 5: Commit**

```bash
git add docs/CAPABILITY_EVIDENCE.md infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs
git commit -m "docs(ST-48): add current capability evidence matrix"
```

### Task 2: Reconcile product and architecture claims

**Files:**
- Modify: `README.md`
- Modify: `docs/ABOUT.md`
- Modify: `docs/PROJECT_BRIEF.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/qa/ST-31-visual-accessibility-regression.md`
- Modify: `infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

**Interfaces:**
- Consumes: the Task 1 matrix and ST-31/ST-49 production QA reports.
- Produces: one current public product flow and a component status table with honest evidence levels.

- [ ] **Step 1: Add failing stale-claim assertions**

Assert that the active product documents use separate `Save` and `Share` actions, no longer describe the original-song UI or hosted journey as planned, link to the evidence matrix, and mark ST-31 production verification complete while pointing physical-device work to ST-52.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `node --test infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

Expected: failure on the current `Save & share`, planned-song, pending-hosted-flow, and ST-31-local-only text.

- [ ] **Step 3: Update the five product/architecture documents**

Describe the current one-page flow: append and reorder selected media, choose original song/instrumental/no music, consent, generate, preview with cover, Make again, Save, and Share. Cite ST-49 for hosted browser proof, ST-31 for accessibility proof, Agent Engine run `34024861486`, and ST-52 for the remaining physical-device boundary.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `node --test infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

- [ ] **Step 5: Commit**

```bash
git add README.md docs/ABOUT.md docs/PROJECT_BRIEF.md docs/ARCHITECTURE.md docs/qa/ST-31-visual-accessibility-regression.md infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs
git commit -m "docs(ST-48): reconcile product and architecture status"
```

### Task 3: Reconcile UX and design QA

**Files:**
- Modify: `docs/ux/MOBILE_PRODUCTION_FLOW.md`
- Modify: `design-qa.md`
- Modify: `docs/prompts/memory-director-prompts.md`
- Modify: `infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

**Interfaces:**
- Consumes: `apps/web/src/components/ProductionWizard.tsx`, its tests, ST-31, and ST-49.
- Produces: current ready/preparing/preview/saved/error interaction states and current visual/accessibility evidence.

- [ ] **Step 1: Add failing UX vocabulary assertions**

Require `Clear all`, `Make again`, `Save video`, and `Share video` in the mobile flow; reject `Save & share` from active UX, design-QA, and prompt documents.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `node --test infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

- [ ] **Step 3: Rewrite the current UX states and refresh design QA**

Show the horizontal thumbnail strip, drag/keyboard reorder, three soundtrack radios, permission checkbox, fixed Make action, retained prior preview during Make again, cover/poster, separate Save/Share, and failure recovery. Record desktop/mobile browser evidence and explicitly leave native touch, microphone, device storage, and share sheet to ST-52.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `node --test infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

- [ ] **Step 5: Commit**

```bash
git add docs/ux/MOBILE_PRODUCTION_FLOW.md design-qa.md docs/prompts/memory-director-prompts.md infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs
git commit -m "docs(ST-48): align UX and design QA with production"
```

### Task 4: Reconcile deployment and operations evidence

**Files:**
- Modify: `docs/operations/AGENT_ENGINE.md`
- Modify: `docs/operations/APP_DEPLOYMENT.md`
- Modify: `docs/operations/public-edge.md`
- Modify: `infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

**Interfaces:**
- Consumes: workflow definitions, non-sensitive Terraform configuration, and successful workflow runs.
- Produces: current hosted-evidence and public-versus-internal URL guidance.

- [ ] **Step 1: Add failing operations assertions**

Require Agent Engine run `34024861486`, release test run `34132016535`, web deployment run `34132225436`, the public homepage and public health route. Reject the obsolete deploy run `32362975036` and judge-facing direct Cloud Run URLs.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `node --test infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

- [ ] **Step 3: Update operations documents**

Replace the unverified Agent Engine warning with the successful smoke evidence and retain the exact future-change gate. Update application deployment to the merged `64ee654` web deployment and public URLs. Clarify that lockdown makes the load balancer the public path and direct Cloud Run routing is restored only as an operator rollback action.

- [ ] **Step 4: Run config and documentation tests**

Run: `npm test --prefix infra/terraform/tools/config-validator`

Expected: all validator, workflow, operations, and documentation tests pass.

- [ ] **Step 5: Commit**

```bash
git add docs/operations/AGENT_ENGINE.md docs/operations/APP_DEPLOYMENT.md docs/operations/public-edge.md infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs
git commit -m "docs(ST-48): refresh deployed operations evidence"
```

### Task 5: Reconcile demo and submission materials

**Files:**
- Modify: `docs/demo/DEMO_RUNBOOK.md`
- Modify: `docs/submission/DEVPOST_PROJECT_PAGE.md`
- Modify: `docs/submission/DEMO_SCRIPT.md`
- Modify: `docs/submission/SUBMISSION_CHECKLIST.md`
- Modify: `docs/submission/EVIDENCE_PACKAGE.md`
- Modify: `infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

**Interfaces:**
- Consumes: the capability matrix, current public URL, ST-49 browser evidence, and open ST-17/ST-9/ST-52 gates.
- Produces: recording and submission copy that matches the deployed product without claiming final human artefacts.

- [ ] **Step 1: Add failing submission consistency assertions**

Require current commit/workflow evidence and separate Save/Share language. Require the rights register, public video, Devpost receipt, and physical-device evidence to remain incomplete.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `node --test infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

- [ ] **Step 3: Update all demo and submission documents**

Use verified hosted browser behavior as engineering evidence while keeping ST-17 final video, ST-9 rights approval, ST-52 physical-device behavior, roster/eligibility, track selection, public video URL, and receipt as explicit human release gates. Remove stale workflow references and use `https://memorydirector.com/` for judging.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `node --test infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs`

- [ ] **Step 5: Commit**

```bash
git add docs/demo/DEMO_RUNBOOK.md docs/submission/DEVPOST_PROJECT_PAGE.md docs/submission/DEMO_SCRIPT.md docs/submission/SUBMISSION_CHECKLIST.md docs/submission/EVIDENCE_PACKAGE.md infra/terraform/tools/config-validator/test/documentation-consistency.test.mjs
git commit -m "docs(ST-48): align demo and submission evidence"
```

### Task 6: Final validation and handoff

**Files:**
- Verify: all files changed in Tasks 1–5

**Interfaces:**
- Consumes: completed documentation changes.
- Produces: reviewed branch, green CI, PR, and Linear evidence while ST-48 remains In Progress until merge and rendered-link checks.

- [ ] **Step 1: Scan for prohibited and stale claims**

Run targeted `rg` checks for `Save & share`, obsolete workflow runs, old hosted URLs, planned-song language, pending ST-31 language, and the prohibited README wording. Review every remaining match and preserve only historical or explicitly pending evidence.

- [ ] **Step 2: Run all relevant local checks**

Run the config-validator suite, API tests, consent-writer tests, ClickHouse bootstrap tests, web tests, and web production build. Expected totals at the starting baseline are API 193, consent writer 9, ClickHouse 6, and web 47; documentation tests add to the validator total.

- [ ] **Step 3: Review rendered Markdown and public links**

Inspect the GitHub-rendered Markdown diff after pushing. Open `https://memorydirector.com/` and `https://memorydirector.com/api/health`; confirm public routing without following direct Cloud Run URLs.

- [ ] **Step 4: Request focused review and resolve findings**

Review against Linear ST-48, especially evidence-level distinctions, link validity, contradictory wording, and accidental completion claims for ST-17, ST-9, or ST-52.

- [ ] **Step 5: Open the PR and update Linear**

Create a human-readable PR with the exact verification results. Keep ST-48 In Progress until the PR is merged and its rendered Markdown/public-link evidence is recorded.
