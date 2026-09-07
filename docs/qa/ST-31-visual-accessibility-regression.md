# ST-31 visual and accessibility regression QA

## Scope and ownership

- Production baseline: <https://memorydirector.com/>
- Baseline commit: `6ed4dbd`
- Test date: 7 September 2026 (AEST)
- Browser: isolated Chromium
- Synthetic media only; no media was submitted to the production generation API.
- Completed [ST-49 live browser acceptance](ST-49-LIVE-BROWSER-ACCEPTANCE.md)
  supplies production generation, preview, playback, Make again, and Save
  evidence. ST-52 now owns the remaining physical-device acceptance.

## Browser and device matrix

| Environment | Viewport | Status | Evidence |
| --- | ---: | --- | --- |
| Production Chromium, desktop emulation | 1280 × 720 | Pass with ISSUE-001 found | Layout, form semantics, typed input, media selection, reorder, removal, Clear all, limit handling, and console checked |
| Production Chromium, mobile emulation | 390 × 844 | Pass with ISSUE-001 found | No horizontal overflow; responsive layout and controls checked |
| Production Chromium, narrow mobile emulation | 320 × 568 | Pass with ISSUE-001 found | No horizontal overflow; visible controls meet the 44px target minimum |
| ST-49 production journey, desktop and mobile emulation | Desktop and 390 × 844 | Pass | Original-song and no-music generation, progress, 60-second preview, playback, Make again, and Save passed; phone-only follow-up moved to ST-52 |
| Local production build, desktop emulation | 1280 × 720 | Pass | ISSUE-001 contrast remeasured after the fix; no console errors |
| Local production build, mobile emulation | 390 × 844 | Pass | Post-fix responsive and keyboard regression; no horizontal overflow or console errors |
| Physical iOS or Android device | Native | Pending in ST-52 | Required for native picker, touch reorder/scroll, device Save, native Share completion/cancellation, and the instrumental rerun |

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

Severity: Medium. Status: fixed locally.

The production palette rendered multiple normal-sized labels below the WCAG AA
4.5:1 contrast threshold. Measured examples included 3.56:1 for the masthead
subtitle, 3.77:1 for terracotta helper text, 4.19:1 for moss text on sand,
3.04:1 for the request placeholder, and 3.28:1 for the composited preview
badge.

The fix darkens the three affected palette tokens, uses the muted token for
placeholder text, and changes the preview badge to a subtle dark overlay.
Post-fix browser-computed ratios are:

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
- Post-fix Chromium console: no errors.

QA found one Medium accessibility issue and fixed it locally. Under the QA
health rubric, the inspected page improves from 98.8 to 100 after the fix.

## Remaining before ST-31 can be Done

1. Incorporate ST-52's physical iOS or Android evidence when that follow-up is
   complete.
2. Verify the merged contrast fix on the deployed production URL.
