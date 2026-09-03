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
        if resolved_api_key:
            self._client = genai.Client(api_key=resolved_api_key)
        else:
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            if not project:
                raise KeyError("GOOGLE_CLOUD_PROJECT")
            self._client = genai.Client(
                vertexai=True,
                project=project,
                location=os.environ.get("LYRIA_LOCATION", "global"),
            )
        self._model = model

    def generate(self, prompt: str) -> GeneratedSong:
        try:
            interaction = self._client.interactions.create(model=self._model, input=prompt)
            outputs = getattr(interaction, "outputs", None) or []
            audio = next((output for output in outputs if getattr(output, "type", None) == "audio"), None)
            lyrics = "\n".join(
                output.text
                for output in outputs
                if getattr(output, "type", None) == "text" and getattr(output, "text", None)
            )
            if audio is None or not getattr(audio, "data", None):
                raise ValueError("Lyria did not return audio.")
            return GeneratedSong(
                audio=base64.b64decode(audio.data),
                lyrics=lyrics,
                model=self._model,
            )
        except Exception as error:
            raise RuntimeError("Original song generation is unavailable.") from error
