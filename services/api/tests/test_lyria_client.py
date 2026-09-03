import base64
import sys
import types

import pytest

from app.lyria_client import GoogleLyriaClient


def test_lyria_client_returns_audio_lyrics_and_model(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeInteractions:
        def create(self, **kwargs: object):
            calls.update(kwargs)
            return types.SimpleNamespace(
                outputs=[
                    types.SimpleNamespace(type="text", text="[Verse] Garden sunshine"),
                    types.SimpleNamespace(type="audio", data=base64.b64encode(b"song-bytes").decode()),
                ],
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


def test_lyria_client_reads_audio_and_lyrics_from_interaction_outputs(monkeypatch) -> None:
    class FakeInteractions:
        def create(self, **kwargs: object):
            return types.SimpleNamespace(
                outputs=[
                    types.SimpleNamespace(type="text", text="[Verse] Garden sunshine"),
                    types.SimpleNamespace(type="audio", data=base64.b64encode(b"song-bytes").decode()),
                ]
            )

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            self.interactions = FakeInteractions()

    fake_google = types.ModuleType("google")
    fake_google.genai = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "google", fake_google)

    song = GoogleLyriaClient(api_key="test-key").generate("original garden song")

    assert song.audio == b"song-bytes"
    assert song.lyrics == "[Verse] Garden sunshine"


def test_lyria_client_uses_vertex_service_account_credentials_when_no_api_key_exists(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeInteractions:
        def create(self, **kwargs: object):
            return types.SimpleNamespace(
                outputs=[
                    types.SimpleNamespace(type="text", text="garden song"),
                    types.SimpleNamespace(type="audio", data=base64.b64encode(b"song-bytes").decode()),
                ],
            )

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            calls.update(kwargs)
            self.interactions = FakeInteractions()

    fake_google = types.ModuleType("google")
    fake_google.genai = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "memory-director")
    monkeypatch.delenv("LYRIA_LOCATION", raising=False)

    GoogleLyriaClient().generate("original garden song")

    assert calls == {"vertexai": True, "project": "memory-director", "location": "global"}


def test_lyria_client_turns_provider_failures_into_a_safe_runtime_error(monkeypatch) -> None:
    class FailingInteractions:
        def create(self, **kwargs: object):
            raise ValueError("provider unavailable")

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            self.interactions = FailingInteractions()

    fake_google = types.ModuleType("google")
    fake_google.genai = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "google", fake_google)

    with pytest.raises(RuntimeError, match="Original song generation is unavailable"):
        GoogleLyriaClient(api_key="test-key").generate("original garden song")
