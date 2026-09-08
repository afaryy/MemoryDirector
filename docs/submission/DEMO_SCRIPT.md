# Three-minute demo script

This script is for an English-subtitled recording. Use only media marked
approved in [`docs/demo/MEDIA_RIGHTS_REGISTER.md`](../demo/MEDIA_RIGHTS_REGISTER.md).
The spoken lines are intentionally short so the product behaviour, not a
slide deck, remains the focus.

| Time | On screen | Voiceover / subtitle | Evidence to capture |
| --- | --- | --- | --- |
| 0:00–0:15 | Open the phone-sized Memory Director page. | “My mother takes beautiful photos, but making a short film is still too complicated.” | Lived family problem, large controls, typed fallback visible. |
| 0:15–0:35 | Type or speak the request and deliberately select approved photos/videos. | “I want to remember this cheerful garden visit.” | Browser receives only selected media; permission confirmation is visible. |
| 0:35–0:55 | Press **Make my film**. | “One request is enough. Memory Director prepares the moments I selected.” | Compact preparing state; no timeline or required plan-review screens. |
| 0:55–1:15 | Show the portrait preview, selected cover, and playback controls. | “It makes a 60-second preview that I can simply watch.” | Actual visible output only; do not claim a selected/held-back explanation that the UI does not show. |
| 1:15–1:35 | **Release gate:** show the original-memory-song option only if the approved-fixture rehearsal succeeds. | “The song is made from the memories I approved, not copied from a favourite singer.” | Capture the user-facing result and retain safety/provenance evidence; otherwise use instrumental or no sound and make no song claim. |
| 1:35–1:55 | **Release gate:** pair the hosted journey with sanitized workflow evidence for the official ClickHouse MCP runtime. | “Before rendering, the guardian checks that these moments are allowed in this film.” | The UI does not show a tool log. Clearly label separate Agent Engine/MCP smoke evidence rather than presenting it as the Web call path. |
| 1:55–2:25 | **Release gate:** show the completed vertical MP4 and tap **Save video**. | “When I am ready, I save the film myself.” | Capture a real visible export and device result; browser UI evidence alone is not a filesystem check. |
| 2:25–2:45 | Tap **Share video** only if ST-52's device rehearsal passes; otherwise show the save-first fallback. | “I choose where to share it. Memory Director never signs in to my social account.” | Native share completion/cancellation or truthful fallback; no social OAuth or direct posting. |
| 2:45–3:00 | Closing card with repository and hosted URL. | “Every memory, directed by you.” | Repository, hosted URL, licence, and ClickHouse track proof. |

## Recording checklist

- Capture the actual hosted product interaction, not a slide replacement.
- Burn in English subtitles and keep every spoken line readable.
- Use a 375px-wide viewport for the mobile flow.
- Keep sanitized ClickHouse MCP evidence in the same recording, clearly separated
  from the visible Web journey.
- Do not expose Secret Manager values, bearer tokens, private GCS URIs, or
  personal media.
- Do not describe a direct API smoke test as a complete hosted UI journey.
- Do not describe desktop or mobile emulation as physical-device evidence.
- Before recording the release-gated rows, verify that the Web page creates the
  preview, invokes the required ClickHouse MCP consent/export path, and exports
  the MP4 through the intended user flow.
- Before publishing, complete the final artefact manifest in
  [`EVIDENCE_PACKAGE.md`](EVIDENCE_PACKAGE.md) and record the final video URL.
