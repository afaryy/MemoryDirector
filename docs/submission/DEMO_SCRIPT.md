# Three-minute demo script

This script is for an English-subtitled recording. Use only media marked
approved in [`docs/demo/MEDIA_RIGHTS_REGISTER.md`](../demo/MEDIA_RIGHTS_REGISTER.md).
The spoken lines are intentionally short so the product behaviour, not a
slide deck, remains the focus.

| Time | On screen | Voiceover / subtitle | Evidence to capture |
| --- | --- | --- | --- |
| 0:00–0:15 | Open the phone-sized Memory Director page. | “My mother takes beautiful photos, but making a short film is still too complicated.” | Lived family problem, large controls, typed fallback visible. |
| 0:15–0:35 | Type or speak the request and deliberately select approved photos/videos. | “I want to remember this cheerful garden visit.” | Browser receives only selected media; permission confirmation is visible. |
| 0:35–0:55 | Press **Make my film**. | “One request is enough. Memory Director chooses the best moments for me.” | Compact preparing state; no timeline or required plan-review screens. |
| 0:55–1:15 | Show the portrait preview and brief explanation of selected/held-back moments. | “It makes an approximately one-minute preview that I can simply watch.” | Actual visible automatic preview only; do not substitute a mock-up. |
| 1:15–1:35 | **Release gate:** show original-memory-song generation only after ST-38 is working. | “The song is made from the memories I approved, not copied from a favourite singer.” | Capture safety result, provenance, and fallback; otherwise show no song claim. |
| 1:35–1:55 | **Release gate:** open the authenticated ClickHouse MCP consent/export check. | “Before saving, the guardian checks that these moments are allowed in this film.” | Capture official MCP tool call and friendly result only after runtime wiring. |
| 1:55–2:25 | **Release gate:** show the completed vertical MP4 and tap **Save & share**. | “When I am ready, I save the film myself.” | Capture a real visible export; direct API smoke evidence is not a substitute. |
| 2:25–2:45 | Show the device share or download result. | “I choose where to share it. Memory Director never signs in to my social account.” | Native-share/download boundary; no social OAuth. |
| 2:45–3:00 | Closing card with repository and hosted URL. | “Every memory, directed by you.” | Repository, hosted URL, licence, and ClickHouse track proof. |

## Recording checklist

- Capture the actual hosted product interaction, not a slide replacement.
- Burn in English subtitles and keep every spoken line readable.
- Use a 375px-wide viewport for the mobile flow.
- Keep the ClickHouse MCP request and its explanation in the same recording.
- Do not expose Secret Manager values, bearer tokens, private GCS URIs, or
  personal media.
- Do not describe a direct API smoke test as a complete hosted UI journey.
- Before recording the release-gated rows, verify that the Web page creates the
  preview, invokes the required ClickHouse MCP consent/export path, and exports
  the MP4 through the intended user flow.
- Before publishing, replace the placeholder in
  [`SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md) with the final video URL.
