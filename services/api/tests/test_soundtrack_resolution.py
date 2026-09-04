from pathlib import Path

import pytest

from app.soundtrack import SoundtrackConfigurationError, resolve_instrumental_track


def test_resolve_instrumental_track_requires_an_existing_absolute_audio_asset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("INSTRUMENTAL_AUDIO_PATH", raising=False)

    with pytest.raises(SoundtrackConfigurationError, match="not configured"):
        resolve_instrumental_track()

    relative_track = Path("music.mp3")
    monkeypatch.setenv("INSTRUMENTAL_AUDIO_PATH", str(relative_track))
    with pytest.raises(SoundtrackConfigurationError, match="absolute"):
        resolve_instrumental_track()

    track = tmp_path / "licensed-bed.mp3"
    track.write_bytes(b"team-owned-audio")
    monkeypatch.setenv("INSTRUMENTAL_AUDIO_PATH", str(track))

    assert resolve_instrumental_track() == track

