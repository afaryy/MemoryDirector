# ST-35 Simple Memory Film UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the multi-stage plan approval interface with the senior-friendly request-to-preview flow defined in the simplified memory-film journey.

**Architecture:** Keep `ProductionWizard` as the client-side orchestration boundary and retain the existing media-analysis, storyboard, render, and export endpoints. Replace its UI state model so a successful storyboard starts rendering automatically after consent; media-analysis results become non-blocking context rather than per-item decisions. Render completion exposes a portrait preview URL extracted from the ZIP response and a single `Save & share` action, with download as the browser fallback.

**Tech Stack:** Next.js 15, React 19, TypeScript, Vitest, Testing Library, existing FastAPI endpoints.

**Spec:** `docs/superpowers/specs/2026-09-03-simplified-memory-film-journey-design.md`

## Global Constraints

- The primary action text is exactly `Make my film`; do not place duration text beside it.
- The browser accepts only 1–15 explicitly selected image/video files and must not claim broad phone-library access or background scanning.
- Selected files can be removed without deleting the device originals.
- The flow has ready, preparing, preview-ready, consent-blocked, generation-failed, and saved states; no timeline or mandatory multi-screen plan review.
- Default output is portrait 9:16 and approximately one minute; generation never publishes to social networks.
- Touch targets remain at least 44 by 44 CSS pixels, with keyboard focus and text alternatives.
- Original-song mode stays bounded by its existing safe API contract and must offer instrumental/no-sound fallback.

---

### Task 1: Lock the simplified journey with behavioral tests

**Files:**
- Modify: `apps/web/src/components/ProductionWizard.test.tsx`

**Interfaces:**
- Consumes: `ProductionWizard` from `./ProductionWizard`.
- Produces: regression coverage for one-click generation, removable selected media, non-blocking media analysis, render preview, retry, and save/share fallback.

- [ ] **Step 1: Write failing tests for the ready and preparing states**

```tsx
it("starts making a film after a request, selected media, and consent", async () => {
  // Set a request, one File, and media permission; click Make my film.
  expect(screen.getByRole("status")).toHaveTextContent("Making your film…");
  expect(screen.queryByRole("button", { name: "Approve plan" })).not.toBeInTheDocument();
});

it("removes one selected item without deleting the other selection", () => {
  // Select two Files; remove the first card.
  expect(screen.queryByText("first.jpg")).not.toBeInTheDocument();
  expect(screen.getByText("second.jpg")).toBeVisible();
});
```

- [ ] **Step 2: Run the focused tests and confirm they fail because the old approval flow is still rendered**

Run: `npm test -- --run src/components/ProductionWizard.test.tsx`

Expected: FAIL because `Make my film` and the single preparing state do not yet implement the requested contract.

- [ ] **Step 3: Write failing tests for preview, retry, and save/share**

```tsx
it("shows the rendered MP4 preview and a Save & share action after export", async () => {
  // Mock /media/analyze, /storyboards, /renders and /renders/export.
  // Mock the export blob as a ZIP containing a fixture MP4 URL via the component helper.
  expect(await screen.findByRole("button", { name: "Save & share" })).toBeEnabled();
  expect(screen.getByLabelText("Your memory film preview")).toBeVisible();
});

it("keeps the request and selected media when generation fails and offers Try again", async () => {
  // Make /storyboards fail after a selected File is present.
  expect(await screen.findByRole("button", { name: "Try again" })).toBeEnabled();
  expect(screen.getByText("garden.jpg")).toBeVisible();
});
```

- [ ] **Step 4: Run the focused tests and confirm they fail for the missing preview/retry behavior**

Run: `npm test -- --run src/components/ProductionWizard.test.tsx`

Expected: FAIL because the current component only exposes a ZIP link and an older plan-approval flow.

- [ ] **Step 5: Commit the red tests**

```bash
git add apps/web/src/components/ProductionWizard.test.tsx
git commit -m "test(ST-35): define simple film journey"
```

### Task 2: Implement one request-to-preview orchestration flow

**Files:**
- Modify: `apps/web/src/components/ProductionWizard.tsx`
- Test: `apps/web/src/components/ProductionWizard.test.tsx`

**Interfaces:**
- Consumes: `POST /media/analyze`, `POST /storyboards`, `POST /renders`, and `POST /renders/export` as currently defined.
- Produces: a `productionState` union (`"ready" | "preparing" | "preview" | "error" | "saved"`) and user-visible preview/save behavior.

- [ ] **Step 1: Replace the blocking decision and approval state with a production state machine**

```ts
type ProductionState = "ready" | "preparing" | "preview" | "error" | "saved";

async function makeFilm() {
  setProductionState("preparing");
  // Analyse selected media, request a constrained storyboard, then render/export.
  // Do not ask for individual keep/hold decisions in this MVP flow.
}
```

- [ ] **Step 2: Keep media analysis and consent boundaries while passing selected media directly to rendering**

```ts
const reviewedMedia = await analyzeMedia(generation);
if (!reviewedMedia || !consentRef.current) return;

const renderMediaIds = reviewedMedia.map((media) => media.media_id);
// Use renderMediaIds in the existing export FormData.
```

- [ ] **Step 3: Parse the ZIP export into browser object URLs and expose only the MP4 preview**

```ts
type ExportArtifacts = { videoUrl: string; downloadUrl: string };

async function readExportArtifacts(blob: Blob): Promise<ExportArtifacts> {
  // Use the platform ZIP reader already available to the app, or add the smallest
  // browser-safe dependency. Locate exactly one .mp4 file; throw a plain error if absent.
}
```

- [ ] **Step 4: Implement retry and save/share behavior**

```ts
async function saveAndShare() {
  if (navigator.share && previewFile) {
    await navigator.share({ files: [previewFile], title: storyboard.title });
    setProductionState("saved");
    return;
  }
  downloadExport();
  setProductionState("saved");
}
```

Use a normal download when Web Share file support is unavailable or rejected. Do not open social accounts or claim sharing occurred when the native share sheet is dismissed.

- [ ] **Step 5: Run the focused component test suite and confirm it is green**

Run: `npm test -- --run src/components/ProductionWizard.test.tsx`

Expected: PASS, including existing accessibility and consent-reset coverage updated to the new flow.

- [ ] **Step 6: Commit the orchestration implementation**

```bash
git add apps/web/src/components/ProductionWizard.tsx apps/web/src/components/ProductionWizard.test.tsx apps/web/package.json apps/web/package-lock.json
git commit -m "feat(ST-35): simplify memory film generation"
```

### Task 3: Apply the mobile-first visual system and responsive layout

**Files:**
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/src/app/page.tsx`
- Test: `apps/web/src/app/page.test.tsx`

**Interfaces:**
- Consumes: the `ProductionWizard` semantic regions, button labels, status role, and preview media element from Task 2.
- Produces: a compact, responsive, accessible screen that does not require a timeline or multi-stage review.

- [ ] **Step 1: Write a failing page-level test for the concise product framing**

```tsx
it("frames Memory Director as a simple request-to-film tool", () => {
  render(<HomePage />);
  expect(screen.getByText("Turn phone moments into a short film.")).toBeVisible();
  expect(screen.queryByText(/plan stays in your control/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the page test and confirm it fails on the old review-oriented copy**

Run: `npm test -- --run src/app/page.test.tsx`

Expected: FAIL because review-oriented text remains in the rendered page/component boundary.

- [ ] **Step 3: Restyle the screen using the approved compact blue direction**

```css
/* Swiss anchor: #f7f7f8 surface, #17324d type, #1f5ea8 accent,
   one-pixel rules, Helvetica/Arial family, and no decorative texture. */
.wizard { max-width: 48rem; padding-block: .75rem 2rem; }
.wizard__ready, .wizard__preview { border: 1px solid #cdd8e2; border-radius: 16px; }
.wizard__preview video { aspect-ratio: 9 / 16; max-height: min(54vh, 38rem); }
```

Keep headings compact; avoid forced headline wrapping on standard desktop widths. Make all primary and removal controls at least 44px high.

- [ ] **Step 4: Run page and component tests, then build the Web app**

Run: `npm test -- --run src/app/page.test.tsx src/components/ProductionWizard.test.tsx && npm run build`

Expected: PASS and Next.js production build exits 0.

- [ ] **Step 5: Commit the visual implementation**

```bash
git add apps/web/src/app/globals.css apps/web/src/app/page.tsx apps/web/src/app/page.test.tsx
git commit -m "feat(ST-35): present compact mobile film flow"
```

### Task 4: Verify and prepare the required pull request

**Files:**
- Verify: `apps/web/src/components/ProductionWizard.tsx`
- Verify: `apps/web/src/components/ProductionWizard.test.tsx`
- Verify: `apps/web/src/app/globals.css`

**Interfaces:**
- Consumes: completed work from Tasks 1–3.
- Produces: evidence-backed PR description and a clean review branch.

- [ ] **Step 1: Run the complete Web verification suite**

Run: `npm test && npm run build`

Expected: all Web tests pass and the production build exits 0.

- [ ] **Step 2: Perform a local browser smoke test at desktop and 375px mobile width**

Run: `npm run dev`

Expected: the request, picker, removable selected media, generation state, preview state, retry state, and save/share fallback are readable without a timeline or approval step.

- [ ] **Step 3: Inspect the final diff and working tree**

Run: `git diff origin/main...HEAD --check && git status --short`

Expected: no whitespace errors and no unintended generated artifacts.

- [ ] **Step 4: Push and create the PR**

```bash
git push --set-upstream origin feat/ST-35
gh pr create --base main --head feat/ST-35 --title "feat(ST-35): simplify the memory-film flow" --body-file /tmp/st-35-pr.md
```

The PR description must state the exact test/build outputs, explain the browser-only selected-media boundary, and list remaining unverified runtime work without claiming a completed hosted journey.

## Plan self-review

- **Spec coverage:** Tasks 1–3 cover ready, preparing, preview, error, saved, selected-media removal, consent, approximately-one-minute framing, safe sound choices, responsive accessibility, and the removal of mandatory plan review. The ClickHouse runtime gate stays a documented dependency and is not falsely claimed as implemented by this UI task.
- **Placeholder scan:** No task uses a deferred implementation placeholder; the ZIP-read choice is constrained to a browser-safe smallest dependency or an existing platform API, and its failure behavior is explicit.
- **Type consistency:** `ProductionState`, `makeFilm`, `readExportArtifacts`, and `saveAndShare` are defined in Task 2 and consumed only within `ProductionWizard`; Task 3 uses semantic regions created there.
