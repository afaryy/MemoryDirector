# ST-52 Physical iPhone Evidence and ST-48 Reconciliation Plan

**Goal:** Record the completed physical-iPhone QA pass and reconcile every active capability, architecture, UX, operations, demo, and submission claim with current `main` at `eab585c` and the deployed Web release at `6b738f4`.

**Baseline:** `origin/main` at `eab585c9f8db6bbf14143c8e5c61c24c7cf2ecca`; successful current-main Tests run `34191468668`; deployed Web release `6b738f40014e4c7861ff1705f7df4d26d294d051`; successful manual Web deployment run `34188310631`.

**Constraints:** Preserve private media and secrets, distinguish user-attested physical-device results from automated evidence, record unavailable device metadata as unavailable rather than guessing, and keep Linear issues In Progress until their documentation PR is merged and rendered evidence is verified.

## Task 1: Re-audit today's merged changes

- [x] Review PRs #123–#128 and their source/test/documentation changes.
- [x] Compare active documentation with current iOS preview, private thumbnail, consent-copy, desktop-local fallback, and deployment behavior.
- [x] Add failing documentation-consistency assertions for any stale claims found.

## Task 2: Record the ST-52 all-pass physical iPhone report

- [x] Create `docs/qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md` with date, release, environment, privacy-safe evidence, and pass outcomes.
- [x] Update the ST-49 handoff so it points to the completed physical-device report.
- [x] Mark unknown device/browser version fields explicitly as not supplied unless the tester provides them.
- [x] Update the capability matrix and other active documents to distinguish physical-iPhone proof from untested Android behavior.

## Task 3: Reconcile ST-48 against the final release

- [x] Update product, architecture, UX, design-QA, operations, demo, and submission documents affected by PRs #123–#128.
- [x] Replace the former `64ee654`/`01c7e48` release references with the final `6b738f4` release and current successful workflow evidence.
- [x] Record completed ST-9 rights approval while preserving the open final-recording and Devpost-submission gates.

## Task 4: Verify and review

- [x] Run the focused documentation-consistency test, full config-validator suite, API tests, consent-writer tests, ClickHouse tests, Web tests, and Web production build.
- [x] Scan for stale release hashes, obsolete ST-52-pending wording, broken links, and overclaims.
- [x] Review the complete diff against ST-48 and ST-52 acceptance boundaries.

## Task 5: Prepare delivery

- [x] Commit the evidence and reconciliation changes on `docs/ST-52-ST-48-final-evidence`.
- [x] Push and open a PR with exact verification results.
- [x] Update Linear ST-52 and ST-48 with the PR/evidence while keeping closure dependent on merge and final rendered-link verification.
