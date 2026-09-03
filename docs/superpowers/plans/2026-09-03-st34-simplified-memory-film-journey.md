# ST-34 Simplified Memory Film Journey Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align current product documentation with the approved one-request, one-preview, one-save journey without representing unimplemented features as working.

**Architecture:** Documentation-only alignment. The approved ST-34 specification is the source of truth; public product documents state enduring workflow contracts, while submission and demo documents label capabilities pending until verified. No API, web, Terraform, dependency, or render code changes are made.

**Tech Stack:** Markdown, Git, existing Vitest web baseline.

**Spec:** `docs/superpowers/specs/2026-09-03-simplified-memory-film-journey-design.md`

## Global Constraints

- Use `docs/ST-34`; do not change application, infrastructure, dependency, or lock files.
- The primary UI action is exactly `Make my film`; no duration helper copy beside it.
- Describe a default approximately-one-minute, 9:16 film; do not promise a timeline editor, whole-library browsing, direct social publishing, or a commercial-song catalogue.
- Browser MVP media access is limited to files deliberately selected through a device/browser picker.
- Preserve an explicit consent/export gate. State the ClickHouse MCP path as a required runtime gate only where reproducible evidence exists.
- Describe the original AI memory song as intended ST-38 work, with safety constraints and an instrumental/no-sound fallback; do not claim Lyria is deployed or proven.
- Do not add `hackathon` to `README.md`.
- Every public claim must agree with the ST-34 specification or be labeled pending.

---

### Task 1: Align top-level product and architecture documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/ABOUT.md`
- Modify: `docs/PROJECT_BRIEF.md`
- Modify: `docs/ARCHITECTURE.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-09-03-simplified-memory-film-journey-design.md`.
- Produces: A consistent overview for contributors, judges, and ST-35/ST-36/ST-38.

- [ ] **Step 1: Record stale workflow language**

Run:

```bash
rg -n '45.?60|approve the (final )?plan|storyboard before|plan review' README.md docs/ABOUT.md docs/PROJECT_BRIEF.md docs/ARCHITECTURE.md
```

Expected: Existing documents contain the old duration range and multi-stage review language.

- [ ] **Step 2: Rewrite the product contract**

Apply these rules:

- `README.md`: approximately-one-minute vertical film and concise confirmation before save/share; retain manual sharing and consent safeguards.
- `docs/ABOUT.md`: replace proposed-plan/final-plan wording with “generates a preview and gives one concise confirmation before saving.” Retain uncertain-fact and non-publication rules.
- `docs/ARCHITECTURE.md`: identify constrained storyboard, deterministic renderer, and ClickHouse MCP consent/export gate. Statuses must say which renderer/song capabilities remain pending verification.

- [ ] **Step 3: Check scope**

Run:

```bash
rg -n -i 'whole.*library|automatic.*publish|commercial song|timeline editor' README.md docs/ABOUT.md docs/PROJECT_BRIEF.md docs/ARCHITECTURE.md
```

Expected: No document promises an excluded capability; explicit denials are allowed.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/ABOUT.md docs/PROJECT_BRIEF.md docs/ARCHITECTURE.md
git commit -m "docs(ST-34): align product journey"
```

### Task 2: Replace obsolete mobile flow and align prompt contracts

**Files:**
- Modify: `docs/ux/MOBILE_PRODUCTION_FLOW.md`
- Modify: `docs/prompts/memory-director-prompts.md`

**Interfaces:**
- Consumes: the ST-34 specification and Task 1 language.
- Produces: UI behavior and prompt requirements for ST-35/ST-36/ST-38.

- [ ] **Step 1: Replace the seven-screen wireframe**

Write `Ready`, `Preparing`, `Preview ready`, `Consent blocked`, and `Saved` states. `Ready` includes text request, microphone with typing fallback, removable selected-media cards, and `Make my film`. `Preview ready` includes portrait preview and `Save & share`, not `Approve plan`.

- [ ] **Step 2: Add exact UX acceptance checks**

```text
- A request plus at least one selected file enables Make my film.
- Removing a selected file never deletes the original device file.
- The browser only processes media explicitly selected by the user.
- A failed generation retains the request and selected media for Try again.
- Save & share cannot complete while the consent/export gate denies the request.
- A successful export returns an MP4 and uses the device-native share mechanism when supported.
```

- [ ] **Step 3: Update prompt contracts**

Target exactly `60` seconds, preserve uncertain-fact handling, and require a constrained storyboard rather than direct rendering. Add an original-song contract rejecting named artists, existing song titles/lyrics, and real-person voice imitation; use only approved details and require a no-sound/instrumental fallback.

- [ ] **Step 4: Run terminology checks**

```bash
rg -n 'Approve plan|Approve this plan|45.?60|Create my plan|Continue' docs/ux/MOBILE_PRODUCTION_FLOW.md docs/prompts/memory-director-prompts.md
```

Expected: No obsolete mandatory review action remains. `60` occurs only as the fixed target.

- [ ] **Step 5: Commit**

```bash
git add docs/ux/MOBILE_PRODUCTION_FLOW.md docs/prompts/memory-director-prompts.md
git commit -m "docs(ST-34): simplify production flow"
```

### Task 3: Preserve truthful demo and submission evidence boundaries

**Files:**
- Modify: `docs/submission/SUBMISSION_CHECKLIST.md`
- Modify: `docs/submission/DEVPOST_PROJECT_PAGE.md`
- Modify: `docs/submission/DEMO_SCRIPT.md`
- Modify: `docs/demo/DEMO_RUNBOOK.md`

**Interfaces:**
- Consumes: Tasks 1–2.
- Produces: Truthful evidence requirements for ST-9, ST-17, ST-32, ST-33, ST-36, and ST-38.

- [ ] **Step 1: Update the demo sequence**

Use: family problem; voice/text request; deliberate media selection; `Make my film`; automatic preview; original-song evidence only when working; ClickHouse MCP consent/export check; completed vertical film; `Save & share`. Keep the recording below three minutes and require English subtitles.

- [ ] **Step 2: Separate proof from planned work**

Mark Lyria, visible automatic rendering, Agent Engine, Video Intelligence, and real native-share behavior pending unless a reproducible test/recording link exists. Do not turn an API fixture test into a hosted-UI claim.

- [ ] **Step 3: State rights and sharing boundaries**

Require team-owned, synthetic, public-domain, or recorded-permission media. Label generated music accurately; prohibit copyrighted song/artist/voice-imitation requests. State that export invokes a native share path rather than directly publishing.

- [ ] **Step 4: Verify**

```bash
git diff --check
rg -n 'Approve plan|Approve this plan|45.?60 second|Find moments in your photo library' README.md docs
cd apps/web && npm test -- --run
```

Expected: Active public, UX, prompt, demo, and submission documents agree; historic superseded specs may retain old terminology. Vitest reports 16 passing tests or more.

- [ ] **Step 5: Commit**

```bash
git add docs/submission/SUBMISSION_CHECKLIST.md docs/submission/DEVPOST_PROJECT_PAGE.md docs/submission/DEMO_SCRIPT.md docs/demo/DEMO_RUNBOOK.md
git commit -m "docs(ST-34): align demo evidence"
```

### Task 4: Create a reviewable ST-34 PR

**Files:** None.

**Interfaces:**
- Consumes: commits from Tasks 1–3.
- Produces: A PR linked to ST-34.

- [ ] **Step 1: Inspect the branch**

```bash
git diff --check main...HEAD
git diff --stat main...HEAD
git log --oneline main..HEAD
```

Expected: Only ST-34 specification and documentation files appear.

- [ ] **Step 2: Push and create the PR**

```bash
git push -u origin docs/ST-34
gh pr create --base main --head docs/ST-34 --title "docs(ST-34): simplify the memory-film journey" --body-file /tmp/st-34-pr.md
```

The PR body links ST-34, summarizes the revised journey, states the browser media-access boundary, distinguishes planned Lyria/render work from verified evidence, and reports the exact test result.

- [ ] **Step 3: Record evidence in Linear**

Add the PR URL and check results to ST-34. Keep it In Progress until review, CI, and merge actually succeed.
