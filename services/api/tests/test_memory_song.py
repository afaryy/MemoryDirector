import pytest

from app.memory_song import UnsafeSongRequest, build_memory_song_brief


def test_song_brief_uses_only_approved_memory_details() -> None:
    brief = build_memory_song_brief(
        memory_details=["Mum's garden visit", "two grandchildren laughing"],
        requested_style="warm acoustic pop",
    )

    assert "Mum's garden visit" in brief.prompt
    assert "two grandchildren laughing" in brief.prompt
    assert brief.fallback == "instrumental"


def test_song_brief_allows_an_ordinary_mood_comparison() -> None:
    brief = build_memory_song_brief(
        memory_details=["A sunny garden visit"],
        requested_style="warm and light, like a sunny afternoon",
    )

    assert "warm and light" in brief.prompt


@pytest.mark.parametrize(
    "style_request",
    [
        "Sing exactly like Adele",
        "Use the lyrics from Yesterday",
        "Make this a Beatles cover",
        "In the style of Taylor Swift",
        "Clone my mother's voice",
    ],
)
def test_song_brief_rejects_artist_lyrics_and_voice_imitation(style_request: str) -> None:
    with pytest.raises(UnsafeSongRequest):
        build_memory_song_brief(memory_details=["A sunny garden visit"], requested_style=style_request)
