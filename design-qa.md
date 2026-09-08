# Current design QA

## Compared

- Public product: <https://memorydirector.com/>
- Implementation: `apps/web/src/app/page.tsx`,
  `apps/web/src/components/ProductionWizard.tsx`, and
  `apps/web/src/app/globals.css`
- Audited production commit: `6b738f40014e4c7861ff1705f7df4d26d294d051`
- Browser viewports: desktop and 390 × 844 mobile emulation

## Visual and interaction result

| Area | Current behaviour | Result |
| --- | --- | --- |
| Header and introduction | Compact brand, help action, short outcome-led heading | Pass |
| Media workbench | Mixed-media picker, append, duplicate suppression, ordered cards, cover, move, remove, and confirmed Clear all | Pass |
| Request | Editable textarea with labelled Clear and optional microphone actions | Pass |
| Soundtrack | Original memory song, gentle instrumental, and no-music choices remain visible | Pass |
| Consent and action | Explicit permission gates the fixed, high-contrast Make my film action | Pass |
| Progress and errors | One compact status area; failures preserve inputs and allow retry | Pass |
| Preview | Real 9:16 video, cover, playback, Make again, separate Save and Share actions | Pass |
| Responsive layout | No horizontal overflow at 390 × 844; controls retain usable target sizes | Pass |

## Accessibility result

- Form controls have accessible names and logical keyboard order.
- Focus uses a visible three-pixel outline; disabled actions are distinguishable.
- Epilogue is bundled locally, so visitors do not make a Google Fonts request.
- The deployed contrast fix meets WCAG AA for the measured normal-text pairs:
  muted on sand 4.65:1, terracotta on white 5.49:1, moss on sand
  4.65:1, placeholder on paper 5.78:1, preview badge 5.81:1, and
  media hover 5.78:1.
- Reduced-motion styling is covered by the active CSS regression checks.

## Verification and boundary

- `npm test -- --run`: 53 tests passed across five files on the current release.
- `npm run build`: production build, lint, and type checking passed.
- ST-31 production Chromium check: no console errors in its final desktop or
  mobile pass.
- [ST-31 visual and accessibility regression](docs/qa/ST-31-visual-accessibility-regression.md)
  is Done.
- [ST-49 live browser acceptance](docs/qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md)
  covers production generation in desktop and mobile emulation.
- [ST-52 physical iPhone acceptance](docs/qa/ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md)
  records an all-pass iPhone 11 journey for voice, touch, video preview, Save,
  native Share, and instrumental audio. Android and native screen-reader behavior
  were not tested.
