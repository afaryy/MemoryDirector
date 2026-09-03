# Simplified Memory Film Journey Design

## Purpose

Memory Director helps an older adult independently turn a small, deliberately chosen group of phone photos and videos into a shareable memory film. The experience must replace an editing timeline with one understandable request and one clear save decision.

This specification defines the product contract for ST-35 (mobile UI), ST-36 (automatic rendering), and ST-38 (original AI memory song). It supersedes earlier multi-stage review language for the new production flow; it does not remove the consent requirements that protect media and export.

## Primary journey

1. The person describes the memory by typing or speaking in their own words. Example: “Make a cheerful film from Mum's garden visit.”
2. The person chooses 1–15 photos and/or videos from their device's standard file or photo picker. They can remove a selected item before generating.
3. The person presses **Make my film**.
4. The production crew creates one vertical preview: it selects useful moments, removes redundant material, trims video segments, crops media appropriately, orders the story, adds a title/caption when suitable, chooses sound, and targets an approximately one-minute film.
5. The person watches the preview. One concise confirmation action, **Save & share**, exports the MP4 and invokes the device's native share sheet.

The primary action must not display a duration helper. The product introduction can say that Memory Director makes an approximately one-minute vertical film by default.

## Interaction rules

### Request

- The request field accepts text. A microphone control may populate the same field after speech recognition; typing remains fully available.
- The request can state an occasion, mood, people, place, desired message, and music preference.
- The application must not invent an uncertain place, relationship, or sensitive fact for a title, caption, lyric, or narration.

### Media selection

- Use the operating system or browser-supported picker. The browser MVP only sees files the person deliberately selects.
- The interface must not claim general access to the person's phone library, background scanning, person recognition over the whole library, or automatic search across unselected files.
- Each selected item has an obvious remove action. Selecting more media does not silently remove previously selected items.
- Mixed photos and videos are supported. The first release accepts 1–15 items so a single meaningful clip works while generation time and film quality remain predictable.

### Generation and preview

- The default output is vertical 9:16 and approximately 60 seconds. This is a product default, not an editable timeline value in the MVP.
- The user sees one concise progress state rather than production steps. It must explain that the film is being made, not imply that it has been saved.
- The generated preview may include a short explanation of why particular moments were chosen or held back, but selection review is not a blocking multi-screen workflow.
- A failed generation offers a plain-language retry without discarding the selected media or request.

### Sound and original memory song

- If the request gives a music direction, the system follows it where safe. Otherwise, it derives an appropriate gentle sound direction from the approved request and chosen media.
- The preferred signature experience is an original AI memory song: Gemini uses only approved memory details to prepare simple original lyrics and a music brief, then Lyria produces the song used in the film.
- The user can preview/regenerate the song or choose an instrumental/no-sound fallback before export.
- Reject requests for a named artist, existing song title or lyrics, or imitation of a real person's voice. Do not describe generated audio as copyright-free, exclusive, or a commercial licensed track.
- Store available provenance: generation model/version, safety outcome, duration, and SynthID information where the service provides it.

### Consent and export gate

- Generation does not publish to social networks. The export is a standard MP4 and the device's native share sheet offers destinations such as WeChat, TikTok, YouTube Shorts, Instagram, or X when installed by the user.
- Immediately before the deterministic renderer starts and immediately before export, the Consent Guardian calls the official ClickHouse `mcp-clickhouse` path to check the consent decision, media ownership confirmation, material status, and soundtrack safety record.
- A denied or unavailable required consent record prevents rendering/export. The user receives a simple explanation and can correct the selection or confirmation.
- The agent never directly encodes video. It returns a constrained storyboard; the deterministic render service turns that storyboard into an MP4.

## Non-goals for the MVP

- A timeline editor, templates gallery, or manual trimming controls.
- Whole-library Google Photos, iCloud Photos, or Android gallery indexing.
- Account sign-up, history, cross-device library sync, or direct social-network publishing.
- Claims that a browser can discover unselected media, that sound is free of all rights obligations, or that an uncertain location/person is known.
- A general-purpose non-linear editor.

## User-visible states

| State | Required content | Primary action |
| --- | --- | --- |
| Ready | Request field and selected media control | `Make my film` once input and media are present |
| Preparing | Compact message that the film is being made | No duplicate generation action |
| Preview ready | Portrait video preview and brief title/caption, if generated | `Save & share` |
| Consent blocked | Plain-language reason; selected media remains intact | Correct selection or confirmation |
| Generation failed | Plain-language retry message; request and media remain intact | `Try again` |
| Saved | Download/export completed | Native share sheet when supported |

## Cross-device requirements

- The same responsive web application works on desktop and mobile. Mobile is the primary production surface; desktop supports a demo or family assistance.
- Touch targets are at least 44 by 44 CSS pixels; text, contrast, focus states, and keyboard operation meet the existing accessibility baseline.
- File selection must use browser capabilities that work on current iOS and Android browsers where supported. The application must present a graceful picker/upload fallback rather than a false promise of library search.

## Technical handoff

### ST-35 — mobile UI

Implement the five user-visible states above in one responsive screen flow. Keep the primary action text exactly `Make my film`; do not add duration text adjacent to it. Maintain removable selected-media chips/cards and a single confirmation route from preview to save.

### ST-36 — automatic film renderer

Accept a constrained storyboard and selected media metadata, not free-form model commands. Produce a 9:16 approximately 60-second MP4 by using deterministic duration allocation, crop rules, video trim points, ordering, transitions, titles/subtitles, and mixed audio. Enforce the ClickHouse MCP Consent Guardian before render and export; test the denial path.

### ST-38 — original memory song

Accept only the approved request and selected-media facts needed for a music brief. Generate original lyrics/music via approved Google services, record safety/provenance, and provide a graceful instrumental/no-sound fallback that leaves ST-36 able to finish a film.

## Documentation alignment

The following current-main documents describe the earlier multi-screen review flow or a 45–60 second range. ST-34's implementation plan must align their product claims with this specification without claiming that unimplemented UI or services already exist:

- `README.md`: change the product-duration and workflow description to the default approximately one-minute film and concise confirmation model.
- `docs/ABOUT.md`, `docs/PROJECT_BRIEF.md`, and `docs/ARCHITECTURE.md`: replace mandatory storyboard-review language with the single confirmation/export gate while retaining consent protection.
- `docs/ux/MOBILE_PRODUCTION_FLOW.md`: replace the seven-screen plan/music/storyboard workflow with the states in this specification.
- `docs/prompts/memory-director-prompts.md`: declare a 60-second target and the original-song safety boundary; preserve a safe fallback until ST-38 is implemented.
- `docs/submission/*` and `docs/demo/*`: remain evidence-oriented. They must label any new Lyria, UI, or renderer behavior as pending until actual, reproducible proof exists.

Code remains intentionally unchanged in ST-34. ST-35, ST-36, and ST-38 own implementation; their tests must demonstrate these revised product claims before repository copy can present them as functioning behavior.

## Acceptance checks

- A reviewer can trace every user action from request to native save/share without encountering a timeline or mandatory multi-stage plan review.
- The UI copy never claims broad phone-library access or direct publication.
- The system has exactly one default target: a vertical film of approximately one minute.
- Music safety and consent checks are enforceable, documented interfaces rather than demo-only statements.
- ST-35, ST-36, and ST-38 can implement from this document without redefining the user journey.
