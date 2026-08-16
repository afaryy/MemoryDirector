# Mobile Production Flow — Wireframes and Acceptance Criteria

This is the source-of-truth low-fidelity mobile flow for Memory Director. It is designed for older adults: one primary decision per screen, large labels, and a persistent typed alternative when voice input is unavailable.

## Global interaction rules

- Content column: 16px minimum side margin; no horizontal scrolling.
- Primary controls: at least 52px high with a visible focus state.
- Body text: at least 18px; concise sentences; no editing jargon.
- Every AI action has a plain-language explanation and a clear retry/edit path.
- Media is only selected or held back, never deleted.
- The user must explicitly approve a final plan before rendering or exporting.

## Screen 1 — Request

```text
┌──────────────────────────────────────┐
│ MEMORY DIRECTOR                      │
│                                      │
│ What would you like to remember?     │
│ [ Speak your request               ] │
│                                      │
│ or type it here                       │
│ [ Make a cheerful travel video...  ] │
│                                      │
│                 [ Continue ]         │
└──────────────────────────────────────┘
```

**Acceptance:** voice transcript appears in the editable text field; a microphone failure shows a typing fallback; Continue remains disabled until the request is non-empty.

## Screen 2 — Select media and permission

```text
┌──────────────────────────────────────┐
│ 1 / YOUR PHOTOS AND VIDEOS            │
│ [ Choose photos and videos          ] │
│ 12 items selected                     │
│                                      │
│ ☐ I have permission to use these      │
│   media.                              │
│                                      │
│                 [ Create my plan ]   │
└──────────────────────────────────────┘
```

**Acceptance:** supported photo/video files can be selected; changing selection clears an old plan; Create my plan is disabled until at least one file and permission confirmation are present.

## Screen 3 — Media shortlist

```text
┌──────────────────────────────────────┐
│ 2 / YOUR BEST MOMENTS                 │
│ We chose 12 of 18 items.              │
│                                      │
│ [✓] A03  Harbour sunset  Best light   │
│ [ ] A04  Similar to A03    Held back  │
│ [✓] V02  Family wave      Keeps sound │
│                                      │
│ [ Change selections ] [ Continue ]    │
└──────────────────────────────────────┘
```

**Acceptance:** every asset shows selected or held back with one reason; held-back assets can be restored; no action deletes a source file.

## Screen 4 — Confirm place

```text
┌──────────────────────────────────────┐
│ 3 / ONE QUICK QUESTION                │
│ I think this is the Eiffel Tower.     │
│ Is that right?                        │
│                                      │
│ [ Yes, Eiffel Tower ]                 │
│ [ No, choose another place ]          │
│ [ Leave it out ]                      │
└──────────────────────────────────────┘
```

**Acceptance:** any place below the confidence threshold gets this screen before it appears in title or caption; the user can decline to name it.

## Screen 5 — Music direction

```text
┌──────────────────────────────────────┐
│ 4 / MUSIC FEELING                     │
│ Choose one. You can change it later.  │
│                                      │
│ ○ Gentle festive instrumental          │
│ ○ Warm traditional-inspired            │
│ ○ Bright, calm pop-style instrumental  │
│                                      │
│                    [ Use this music ] │
└──────────────────────────────────────┘
```

**Acceptance:** exactly three rights-safe/generated options are shown with simple names; recommendations can cite confirmed ClickHouse preferences; no commercial-song suggestion is offered without licence proof.

## Screen 6 — Storyboard review

```text
┌──────────────────────────────────────┐
│ 5 / YOUR FILM PLAN                    │
│ A Family Day by the Sea               │
│ Small moments, held close.             │
│                                      │
│ 00–08  Opening photo + title           │
│ 08–26  Harbour and family clips        │
│ 26–55  Sunset and closing message      │
│                                      │
│ [ Change photos ] [ Change music ]    │
│                 [ Approve this plan ] │
└──────────────────────────────────────┘
```

**Acceptance:** title, caption, sequence, place wording, music choice, high-contrast subtitles, and privacy flags are visible; any change revokes approval until the updated plan is reviewed again.

## Screen 7 — Export

```text
┌──────────────────────────────────────┐
│ 6 / YOUR MEMORY FILM                  │
│ Your video is ready.                  │
│ [ Preview video ]                     │
│ [ Save video to phone ]               │
│ [ Save cover and caption ]            │
│                                      │
│ You choose where to share it.          │
└──────────────────────────────────────┘
```

**Acceptance:** render controls remain disabled before approval; successful export includes an MP4, cover image, and copyable caption; no automatic post is made to a social platform.

## End-to-end acceptance scenario

1. User speaks a request, confirms the transcript, selects 15 consented assets, and checks permission.
2. The system presents an explainable selection and asks one uncertain-place question.
3. User selects a music direction informed by a seeded preference, reviews the storyboard, and approves it.
4. The render is accepted only after approval and creates a vertical MP4, cover, and caption.
5. The user saves the package locally without granting a social-platform account permission.
