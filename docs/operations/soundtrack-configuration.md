# Soundtrack configuration

Memory Director can render one of three explicit soundtrack modes:

- `original_song`: a request-scoped song generated through the configured Lyria integration;
- `instrumental`: a team-owned or appropriately licensed local audio asset;
- `no_sound`: no audio stream is added to the film.

To enable `instrumental`, set `INSTRUMENTAL_AUDIO_PATH` in the API runtime to
an absolute path to a packaged `.mp3`, `.m4a`, `.aac`, or `.wav` asset. Keep
the licence/provenance evidence outside of source control with the release
records. Do not use a commercial track, a streaming URL, or a browser-provided
path.

If this setting is absent or invalid, an instrumental export returns a clear
choice error. It does not silently substitute an unlicensed track or source
audio. No soundtrack asset is committed with this repository.
