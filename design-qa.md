# ST-38 design QA

## Compared

- Reference: `.superdesign/tmp/memory-album-workbench.html`
- Implementation: `apps/web/src/app/page.tsx` and `apps/web/src/components/ProductionWizard.tsx`
- Browser: Codex in-app browser
- Desktop viewport: 1280 × 720
- Mobile behavior: responsive rules reviewed at 390 px; automated component behavior verified in Vitest

The in-app browser captures are session artifacts and do not expose filesystem paths. The reference and implementation were captured at the same desktop viewport before comparison.

## Visual comparison

| Area | Reference | Implementation | Result |
| --- | --- | --- | --- |
| Header | Moss film mark, compact brand and help icon | Same hierarchy, colors, spacing and Lucide icons | Pass |
| Intro | Terracotta eyebrow and single-line desktop heading | Heading width and size adjusted to remain on one line | Pass |
| Media | Sand dashed chooser with selected-media guidance | Same; real file input opens the device picker | Pass |
| Request | Paper textarea with inline Clear and microphone actions | Same; both actions are functional and labelled | Pass |
| Music | Three always-visible choices; original song selected | Same; selection styling follows state | Pass |
| Preview | Moss preview-before-save callout | Same; replaced by the real video preview after export | Pass |
| Primary action | Fixed terracotta bottom action | Same; disabled state remains visibly distinct | Pass |

## Interaction and accessibility checks

- Keyboard focus uses a three-pixel terracotta outline.
- The upload control, voice control, clear control, music choices, consent checkbox and primary action all have accessible names.
- The primary action remains disabled until a request, at least one media item and permission are present.
- Epilogue is bundled from `@fontsource/epilogue`; visitors do not make a Google Fonts request.
- Selected items can be removed individually.
- Failed generation keeps the request and media selections and offers retry.
- The generated MP4 appears in a native video preview before Save & Share.

## Verification

- `npm test -- --run`: 13 tests passed.
- `npm run build`: production build passed, including type checking.
- No P0, P1 or P2 visual issues remain in the captured desktop state.
