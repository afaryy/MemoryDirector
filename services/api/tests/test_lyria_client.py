import base64
import sys
import types

from app.lyria_client import GoogleLyriaClient


def test_lyria_client_returns_audio_lyrics_and_model(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeInteractions:
        def create(self, **kwargs: object):
            calls.update(kwargs)
            return types.SimpleNamespace(
                output_audio=types.SimpleNamespace(data=base64.b64encode(b"song-bytes").decode()),
                output_text="[Verse] Garden sunshine",
            )

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            calls["client"] = kwargs
            self.interactions = FakeInteractions()

    fake_google = types.ModuleType("google")
    fake_google.genai = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "google", fake_google)

    song = GoogleLyriaClient(api_key="test-key").generate("original garden song")

    assert calls["client"] == {"api_key": "test-key"}
    assert calls["model"] == "lyria-3-pro-preview"
    assert song.audio == b"song-bytes"
    assert song.lyrics == "[Verse] Garden sunshine"
