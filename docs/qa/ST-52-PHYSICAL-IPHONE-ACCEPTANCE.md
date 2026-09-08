# ST-52 physical iPhone acceptance

Test date: 8 September 2026 (AEST)

Production URL: <https://memorydirector.com/>

## Result

All ST-52 physical-device acceptance checks passed on the tested iPhone. This
closes the iPhone-specific evidence gap left by the automated desktop and mobile
viewport work in [ST-49](ST-49-LIVE-BROWSER-ACCEPTANCE.md).

The results below are tester-observed, physical-device evidence. They are not
automated browser results and do not imply coverage of Android, other iPhone
models, other browsers, or a native screen reader.

## Environment

- Device: iPhone 11
- Operating system: iOS 26.6.1
- Browser: Chrome (version not recorded)
- Audited and deployed Web release: `6b738f40014e4c7861ff1705f7df4d26d294d051`
- Complete release Tests run: [34188276089](https://github.com/afaryy/MemoryDirector/actions/runs/34188276089)
- Manual Web deployment run: [34188310631](https://github.com/afaryy/MemoryDirector/actions/runs/34188310631)

## Physical-device checks

| Area | Result | Observed outcome |
| --- | --- | --- |
| Microphone permission and speech | Pass | Chrome requested microphone permission; speech populated the editable request, and the tester corrected and cleared it. |
| Native mixed-media picker | Pass | The tester selected the required set of real photos and one short video through the iPhone picker. The app used only the deliberately selected items. |
| Video preview | Pass | The selected phone video produced a usable visual preview in the media strip. The release first attempts the local frame and uses the consent-gated private thumbnail fallback only when the mobile frame is unavailable. |
| Touch reorder | Pass | Press-and-hold followed by drag moved a thumbnail to a new position. |
| Clear-all confirmation | Pass | Cancelling preserved the selection; accepting removed the selection as expected. |
| Gentle instrumental render | Pass | A full film completed after the public quota window allowed the request, and instrumental audio was audible. |
| Save video | Pass | The generated MP4 appeared in the expected device location. |
| Native share sheet | Pass | The native share sheet opened; eligible installed messaging destinations appeared and unavailable apps were not presented as direct targets. |

## Privacy-safe evidence

The tester reported the observed outcomes and environment metadata directly. No
raw photos, videos, filenames, account identifiers, screenshots containing
personal media, private storage URIs, or credentials are retained in this report.
The source media remained under the tester's control, and this report records only
pass/fail behavior.

## Evidence boundary

This report completes the physical-iPhone checks required by ST-52. The Web
implementation and release workflows are independently covered by automated
tests, while final rights approval, the public three-minute recording, and the
Devpost submission remain separate release artefacts. Android and physical
screen-reader testing were not part of this pass.
