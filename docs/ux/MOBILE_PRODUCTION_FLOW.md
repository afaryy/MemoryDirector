# Mobile Production Flow

This is the source-of-truth mobile flow for Memory Director. It is designed for older adults: one obvious request, deliberately chosen media, one generated preview, and one save decision. It is a responsive web flow; desktop supports family assistance and demonstration, while mobile is the primary production surface.

## Global interaction rules

- Content has at least 16px side margins and never requires horizontal scrolling.
- Touch targets are at least 44 by 44 CSS pixels and have visible keyboard focus.
- Text uses concise, everyday language; no timeline, trim, template, or rendering jargon is required to complete the journey.
- Voice input populates the editable request field. Typing is always available when speech recognition is unavailable or incorrect.
- The browser only receives media explicitly chosen by the person through its supported picker. It does not scan or search the wider phone library.
- A source photo or video is never deleted. A selected card may be removed from the current film request.
- The default result is an approximately-one-minute vertical 9:16 film. Duration is not shown beside the primary action and is not an editable timeline setting in the MVP.

## Ready

```text
┌──────────────────────────────────────┐
│ MEMORY DIRECTOR                      │
│ What would you like to remember?     │
│ [ Tell us about this memory       ]  │
│                         [ mic ]      │
│                                      │
│ Photos and videos                    │
│ [ Choose from this device ]          │
│ [ beach.jpg × ] [ family.mov × ]     │
│                                      │
│              [ Make my film ]        │
└──────────────────────────────────────┘
```

**Acceptance**

- A request plus at least one selected file enables **Make my film**.
- The microphone is an optional input aid; it never replaces the editable text field.
- The user can remove every selected card before generation. Removing it does not delete the device file.
- The interface asks the user to confirm permission to use the chosen media before processing.

## Preparing

```text
┌──────────────────────────────────────┐
│ Making your film…                    │
│ We are choosing the best moments.    │
│                                      │
│ [ progress indicator ]               │
└──────────────────────────────────────┘
```

**Acceptance**

- The user sees one compact progress state, not a sequence of planning, music, storyboard, and approval screens.
- The system can select useful moments, hold back redundant material, trim video, crop media for portrait, order the story, add concise text, and prepare sound automatically.
- The request and selected media remain available if generation fails.

## Preview ready

```text
┌──────────────────────────────────────┐
│ Your memory film                     │
│                                      │
│ [          9:16 preview           ]  │
│                                      │
│ Garden memories                      │
│ A calm afternoon together.           │
│                                      │
│              [ Save & share ]        │
└──────────────────────────────────────┘
```

**Acceptance**

- The preview contains the selected/automatically curated media in a vertical film.
- A short explanation may name moments selected or held back, but it is not a blocking review workflow.
- If sound was requested, the system follows the safe music direction. Otherwise it selects a gentle direction from the approved request and media.
- Original AI memory-song controls appear only after ST-38 supplies them. Before then, the UI must clearly offer a safe instrumental or no-sound fallback rather than claim a song was generated.

## Consent blocked

```text
┌──────────────────────────────────────┐
│ We need your confirmation first.     │
│ This film cannot be saved yet.        │
│ [ Review selected media ]             │
│ [ Try again ]                         │
└──────────────────────────────────────┘
```

**Acceptance**

- Immediately before rendering and export, the consent/export gate checks the selected-media permission, current selection state, and soundtrack safety through the official ClickHouse MCP path.
- When the gate denies or cannot obtain a required record, it prevents render/export and explains the next safe action in plain language.
- A blocked state never discards the request or the user's selected media.

## Saved

```text
┌──────────────────────────────────────┐
│ Your film is ready.                  │
│ [ Save & share ]                     │
│                                      │
│ You choose where it goes next.       │
└──────────────────────────────────────┘
```

**Acceptance**

- A successful export returns a standard MP4.
- **Save & share** uses the device-native share mechanism where the browser/platform supports it; otherwise it offers a normal download.
- The application never directly posts to WeChat, TikTok, YouTube Shorts, Instagram, X, or another social platform.

## End-to-end acceptance scenario

1. The user speaks or types a request, selects 5–15 consented photos and videos, and confirms permission.
2. The user presses **Make my film** and sees a compact preparing state.
3. The system automatically produces an approximately-one-minute portrait preview and retains the selected media if it needs retrying.
4. The ClickHouse MCP consent/export gate permits the export only when the required records are valid.
5. The user presses **Save & share** and receives an MP4 for a device-controlled destination.
