# ST-31 visual and accessibility regression QA

## Scope and ownership

- Production baseline: <https://memorydirector.com/>
- Verified browser-accessibility commit: `64ee654a999549322dbeea22f9ffc2b8b29acdaf`
- Current production commit: `6b738f40014e4c7861ff1705f7df4d26d294d051`
- Test dates: 7–8 September 2026 (AEST)
- Browser: isolated Chromium
- Synthetic media only; no media was submitted to the production generation API.
- Completed [ST-49 live browser acceptance](ST-49-LIVE-BROWSER-ACCEPTANCE.md)
  supplies production generation, preview, playback, Make again, and Save
  evidence. The later [ST-52 physical iPhone acceptance](ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md)
  records the completed device interaction checks.

## Browser and device matrix

| Environment | Viewport | Status | Evidence |
| --- | ---: | --- | --- |
| Production Chromium, desktop emulation | 1280 × 720 | Pass | Layout, form semantics, typed input, media selection, reorder, removal, Clear all, limit handling, contrast, and console checked |
| Production Chromium, mobile emulation | 390 × 844 | Pass | No horizontal overflow; responsive layout, controls, and deployed contrast checked |
| Production Chromium, narrow mobile emulation | 320 × 568 | Pass before contrast release | No horizontal overflow; visible controls meet the 44px target minimum |
| ST-49 production journey, desktop and mobile emulation | Desktop and 390 × 844 | Pass | Original-song and no-music generation, progress, 60-second preview, playback, Make again, and Save passed; the later ST-52 iPhone follow-up also passed |
| Local production build, desktop emulation | 1280 × 720 | Pass | ISSUE-001 contrast remeasured after the fix; no console errors |
| Local production build, mobile emulation | 390 × 844 | Pass | Post-fix responsive and keyboard regression; no horizontal overflow or console errors |
| iPhone 11, iOS 26.6.1, Chrome (version not recorded) | Native | Pass in ST-52 | Native picker, speech, touch reorder, clear confirmation, device Save, native Share, and instrumental audio passed |
| Android or native screen reader | Native | Not tested | Not implied by the completed iPhone interaction pass |

## Completed interaction checks

- The file picker, request field, Clear, voice input, soundtrack radio group,
  consent checkbox, and primary action have accessible names.
- Keyboard traversal reaches each enabled control in a logical order. Each
  focused control has a visible three-pixel focus indicator; the disabled
  primary action is skipped.
- Typed request entry and Clear work.
- Mixed photo/video selections append, exact duplicates are suppressed, and
  adding media resets prior consent.
- Keyboard reorder changes the media order.
- Individual removal works. Clear all supports both cancellation and
  confirmation, and confirmation resets consent.
- A 16-item selection is rejected without creating a partial selection and
  presents the 15-item limit guidance.
- Voice input exposes a pressed state when browser speech recognition exists.
  Microphone transcription was not exercised.
- Browser accessibility-tree inspection exposes the intended roles, names,
  checked state, and disabled state. A physical screen-reader pass remains
  part of the device check.

## ISSUE-001: secondary text contrast

Severity: Medium. Status: fixed, merged, deployed, and verified.

The production palette rendered multiple normal-sized labels below the WCAG AA
4.5:1 contrast threshold. Measured examples included 3.56:1 for the masthead
subtitle, 3.77:1 for terracotta helper text, 4.19:1 for moss text on sand,
3.04:1 for the request placeholder, and 3.28:1 for the composited preview
badge.

The fix darkens the three affected palette tokens, uses the muted token for
placeholder text, and changes the preview badge to a subtle dark overlay.
Post-deploy browser-computed ratios on `memorydirector.com` are:

| Pair | Ratio |
| --- | ---: |
| Muted on sand | 4.65:1 |
| Muted on paper | 5.78:1 |
| Terracotta on white | 5.49:1 |
| Moss on sand | 4.65:1 |
| Moss on paper (media-picker hover) | 5.78:1 |
| Sand on composited preview badge | 5.81:1 |

A regression test enforces the palette threshold and the two component-level
style connections.

## Automated verification

- `npm test -- --run`: 47 tests passed across five files.
- `npm run build`: production build, lint, and type checking passed.
- Post-deploy Chromium console: no errors.

QA found one Medium accessibility issue and verified its production fix. Under
the QA health rubric, the inspected browser page improves from 98.8 to 100.
ST-31 is Done. The iPhone 11 interaction checks also passed in ST-52. Android
and native screen-reader behavior remain outside this report and do not weaken
the completed browser accessibility evidence.
