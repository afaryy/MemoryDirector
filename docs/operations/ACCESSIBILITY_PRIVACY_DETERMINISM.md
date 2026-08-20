# Accessibility, privacy, and determinism review

This review is the release gate for the older-adult production flow. It combines
automated checks with a short manual pass using a phone-sized viewport and a
keyboard.

## Automated evidence

- Web tests verify that the primary render action is disabled until a plan is
  approved, media consent is checked, and voice input has a typing fallback.
- The voice control exposes `aria-pressed` while listening and status messages
  use a polite live region so a screen reader receives the fallback or request
  result without losing the editable text field.
- API tests verify consent is enforced before storage, provider output cannot
  expose private `gs://` URIs, allow-listed privacy flags remain visible for
  review, and held-back media is never deleted.
- Renderer tests verify the same title, caption, and media bytes produce the
  same render ID while different media bytes cannot collide merely because the
  upload filenames match.

Run the checks locally:

```bash
cd services/api
uv run pytest -q

cd ../../apps/web
npm ci --ignore-scripts
npm run test -- --run
npm run build
```

## Manual checklist

1. Use a 375px-wide viewport and confirm there is no horizontal scroll.
2. Navigate with Tab and Shift+Tab. Every control has a visible focus ring and
   the order follows the request → media → consent → plan → approval flow.
3. Confirm buttons are comfortable to activate (at least 52px high), text is
   concise, and the typed request remains usable when microphone access is
   unavailable.
4. With a screen reader, confirm the listening state and retry/error messages
   are announced, and that the plan cannot be rendered before approval.
5. Upload a fixture containing a permitted privacy signal. Confirm the flag is
   shown for review and that a held-back asset remains available for a later
   decision.
6. Repeat the seeded demo with the same media and copy. Confirm the exported
   package names are stable; change one media byte and confirm the package ID
   changes.

Do not use personal media or real secrets for this review. Only fixtures listed
as approved in `docs/demo/MEDIA_RIGHTS_REGISTER.md` may be used.
