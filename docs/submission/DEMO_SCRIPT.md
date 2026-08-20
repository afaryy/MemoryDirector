# Three-minute demo script

This script is for an English-subtitled recording. Use only media marked
approved in [`docs/demo/MEDIA_RIGHTS_REGISTER.md`](../demo/MEDIA_RIGHTS_REGISTER.md).
The spoken lines are intentionally short so the product behaviour, not a
slide deck, remains the focus.

| Time | On screen | Voiceover / subtitle | Evidence to capture |
| --- | --- | --- | --- |
| 0:00–0:15 | Open the phone-sized Memory Director page. | “I want to make a cheerful travel memory video from these photos.” | Large controls, concise copy, typed fallback visible. |
| 0:15–0:35 | Select the approved album and check permission. | “These are my photos, and I have permission to use them.” | Plan button stays disabled until consent. |
| 0:35–0:55 | Submit the request and show the generated plan. | “Memory Director explains what it chose and what it held back.” | Storyboard title/caption and non-destructive selection reason. |
| 0:55–1:15 | Show the uncertain place prompt and music directions. | “I can confirm this place, leave it out, or choose a different direction.” | No unconfirmed place enters final copy; three rights-safe music feelings. |
| 1:15–1:35 | Open the ClickHouse MCP proof view. | “This recommendation comes from an anonymised preference remembered from an earlier edit.” | Authenticated official MCP `run_query` and friendly explanation. |
| 1:35–1:55 | Show the review screen. Try the render action before approval, then approve. | “Nothing is rendered until I approve the plan.” | Disabled render action, explicit approval, visible privacy checks. |
| 1:55–2:25 | Start the approved export and show the vertical result. | “The result includes a video, a cover, and a caption.” | MP4, cover, high-contrast text, deterministic output package. |
| 2:25–2:45 | Save the package locally. | “I choose where to share it. Memory Director never signs in to my social account.” | Manual save/share boundary; no social OAuth. |
| 2:45–3:00 | Closing card with repository and hosted URL. | “Every memory, directed by you.” | Repository, hosted URL, licence, and ClickHouse track proof. |

## Recording checklist

- Capture the actual hosted product interaction, not a slide replacement.
- Burn in English subtitles and keep every spoken line readable.
- Use a 375px-wide viewport for the mobile flow.
- Keep the ClickHouse MCP request and its explanation in the same recording.
- Do not expose Secret Manager values, bearer tokens, private GCS URIs, or
  personal media.
- Before publishing, replace the placeholder in
  [`SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md) with the final video URL.
