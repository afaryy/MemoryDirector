# Mobile production flow

This is the source-of-truth product flow for Memory Director's responsive,
single-page production experience. Mobile is the primary surface; desktop also
supports family assistance and demonstrations.

## Global interaction rules

- Content has at least 16px side margins and never requires horizontal scrolling.
- Touch targets are at least 44 by 44 CSS pixels and keyboard focus is visible.
- Voice fills the editable request field; typing always remains available.
- The picker exposes only files deliberately selected by the user. The product
  cannot browse or search the wider phone library.
- Removing a selected card or choosing **Clear all** changes only this request; it
  never deletes the device file.
- The output is a 60-second, 9:16 MP4. The user does not edit a timeline.
- The form and generated preview remain on one page.

## 1. Describe and select

```text
┌──────────────────────────────────────┐
│ MEMORY DIRECTOR                      │
│ Turn moments into a film             │
│                                      │
│ Photos and videos        [Clear all] │
│ [ + Choose from this device ]        │
│ [ cover ★ ] [ photo ] [ video ]      │
│ [ ← ] [ → ] [ Remove ]               │
│                                      │
│ What would you like to remember?     │
│ [ Tell us about this memory    ][mic]│
│                                      │
│ Soundtrack                           │
│ (•) Original memory song             │
│ ( ) Gentle instrumental              │
│ ( ) No music                         │
│                                      │
│ [ ] I have permission to use these   │
│             [ Make my film ]         │
└──────────────────────────────────────┘
```

**Acceptance**

- The user selects 1–15 mixed photos and videos and can append another picker
  selection. Exact duplicates are ignored.
- The first item is the cover. Reorder controls change the sequence and cover.
- Clear all asks for confirmation and resets media consent.
- A request, at least one selected item, and permission are required before
  **Make my film** is enabled.
- The three soundtrack choices stay visible. Unsafe or unavailable song generation
  can fall back without claiming success.

## 2. Making the film

```text
┌──────────────────────────────────────┐
│ Making your film…                    │
│ We are choosing the best moments.    │
│ [ progress indicator ]               │
│                                      │
│ Your request and selected media      │
│ remain visible above.                │
└──────────────────────────────────────┘
```

**Acceptance**

- One compact progress area reports the current state; users do not manage separate
  planning, storyboard, music, and render screens.
- The API validates consent before analysis and calls the required ClickHouse MCP
  consent/export guardian immediately before rendering.
- A denied or unavailable required check blocks the render and explains the safe
  next step without discarding the request or selected media.
- A failed generation restores **Make my film** so the user can retry.

## 3. Preview and revise

```text
┌──────────────────────────────────────┐
│ Your film is below                   │
│ Change anything above, then choose   │
│ Make again.                          │
│                                      │
│ [          9:16 preview           ]  │
│ [ play / pause controls ]            │
│                                      │
│ [ Save video ] [ Share video ]       │
└──────────────────────────────────────┘
```

**Acceptance**

- The real MP4 replaces the empty preview state and exposes browser playback.
- The selected cover is visible while the video is not playing.
- Changes to media, request, permission, or soundtrack can be rendered with
  **Make again**; source files remain untouched.
- **Save video** starts a normal MP4 download.
- **Share video** opens the native file share sheet when supported. When it is not,
  the interface tells the user to save first and share from WhatsApp, WeChat, or
  another app themselves.
- The application never directly posts to a social platform.

## Evidence boundary

Desktop and 390 × 844 browser journeys are verified in
[ST-49 live browser acceptance](../qa/ST-49-LIVE-BROWSER-ACCEPTANCE.md).
Physical-device picker, voice permission, touch reorder/scroll, saved-file location,
native Share completion/cancellation, and the instrumental rerun remain in ST-52.
See the [capability evidence matrix](../CAPABILITY_EVIDENCE.md) before turning a
browser result into a device or final-submission claim.
