# ST-49 live browser acceptance

Date: 7 September 2026

Production URL: <https://memorydirector.com>

Google Cloud project: `memory-director-505708`

## Result

The ST-49 automated browser scope passed on desktop and at a 390 x 844 mobile viewport. A user can select mixed media, describe the memory, choose a soundtrack mode, generate a 60-second vertical film without leaving the page, preview it, and save it.

ST-49 is complete for that automated scope. The subsequent [ST-52 physical
iPhone pass](ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md) verified native microphone,
touch, device Save, native Share, and the instrumental render on an iPhone 11.

## Environment evidence

- API image: `australia-southeast1-docker.pkg.dev/memory-director-505708/memory-director-sandbox/api:7f9a7484e8ffb6d6cfd584bc21e967716b3c3b4b`
- Cloud Run revision: `memory-director-sandbox-api-00019-xzx`
- API deployment workflow run: `34127866347`
- Production fix: [PR #116](https://github.com/afaryy/MemoryDirector/pull/116)

## Browser checks

| Area | Desktop | Mobile viewport | Evidence |
| --- | --- | --- | --- |
| Page and health | Pass | Pass | Production page loaded through the public domain. |
| Mixed media | Pass | Pass | JPG and MP4 items appeared with distinct Photo/Video labels. |
| Append selection | Pass | Pass | A later picker selection preserved earlier items. |
| Exact duplicate | Pass | Pass | Reselecting the same file reported that it was already selected. |
| Horizontal strip | Pass | Pass | Thumbnails remained visual and horizontally scrollable. |
| Reorder | Not separately exercised | Pass with keyboard | At the mobile viewport, Space, ArrowRight, Space changed the first two items; mouse drag and physical touch remain pending. |
| Remove one | Pass | Pass | Item count changed from four to three. |
| Clear all | Pass | Pass | Selection returned to zero. Dialog cancel is pending because the automation surface did not expose the confirm dialog. |
| 15-item boundary | Pass | Pass | Exactly 15 accepted; 16 rejected with a clear message. |
| Request and Clear | Pass | Pass | Typed text was cleared and could be re-entered. |
| Consent gate | Pass | Pass | Make button remained disabled until media, request, and consent were present. |
| Original AI song | Pass | Pass UI | Production export completed with generated audio. |
| No music | Pass UI | Pass | Production export completed. |
| Gentle instrumental | Selected | Pending rerun | Public quota guard returned `Please try again later.` before the request reached Cloud Run. |
| In-page progress | Pass | Pass | Inputs were disabled during work; status advanced without route navigation. |
| Preview | Pass | Pass | Ready MP4 was 60.0 seconds, 1080 x 1920, and had a non-empty poster. |
| Playback | Pass | Pass | Current time advanced while playing. |
| Save | Pass | Pass UI | Page reported `Video saved to this device.` |
| Share | Pending physical device | Pending physical device | Native WhatsApp/WeChat destinations depend on installed apps and the device share sheet. |
| Make again | Pass UI | Guard verified | Control remained on the same page; rerun encountered the configured quota guard. |

## Production defect found and resolved

The first live run exposed a Firestore schema error in the quota store:

```text
google.api_core.exceptions.InvalidArgument: 400 field name '__once__' is reserved.
```

ST-50 added a regression test and replaced the reserved field. After PR #116 was merged and the API deployed, the same mixed-media flow returned storyboard HTTP 201 and a successful render.

## Media integrity note

The privacy-safe test images are intentionally synthetic marker cards with distinct colors and labels. The first marker appeared in the opening segment and the second marker appeared later in the film. That visible transition verifies that the renderer used the selected source bytes and preserved multi-source sequencing.

## ST-52 physical-device completion

The follow-up checks were completed on 8 September 2026 on an iPhone 11 running
iOS 26.6.1 in Chrome (version not recorded):

1. Allow microphone access only for the test, speak a short request, correct it, and clear it.
2. Select real photos and videos through the native picker and press-drag a thumbnail to reorder it.
3. Generate one film after the quota window resets and confirm the instrumental track is audible.
4. Save the MP4 and verify it appears in the device's expected download/photo location.
5. Open the native share sheet and verify WhatsApp or WeChat appears only when installed.
6. Cancel the clear-all confirmation once, then accept it once.

All six checks passed. See the [ST-52 physical iPhone acceptance report](ST-52-PHYSICAL-IPHONE-ACCEPTANCE.md)
for observed outcomes and privacy-safe evidence boundaries. Android and native
screen-reader coverage are not implied by the iPhone result.
