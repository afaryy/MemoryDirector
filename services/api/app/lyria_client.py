import base64
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedSong:
    audio: bytes
    lyrics: str
    model: str


class GoogleLyriaClient:
    def __init__(self, api_key: str | None = None, model: str = "lyria-3-pro-preview") -> None:
        from google import genai

        resolved_api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_api_key:
            raise KeyError("GEMINI_API_KEY")
        self._client = genai.Client(api_key=resolved_api_key)
        self._model = model

    def generate(self, prompt: str) -> GeneratedSong:
        interaction = self._client.interactions.create(model=self._model, input=prompt)
        audio = getattr(interaction, "output_audio", None)
        if audio is None or not getattr(audio, "data", None):
            raise RuntimeError("Lyria did not return audio.")
        return GeneratedSong(
            audio=base64.b64decode(audio.data),
            lyrics=getattr(interaction, "output_text", "") or "",
            model=self._model,
        )
