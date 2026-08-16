import os
from typing import Protocol

from app.models import Storyboard
from app.prompts import build_storyboard_prompt


class GeminiGateway(Protocol):
    def generate_json(self, prompt: str, schema: type[Storyboard]) -> Storyboard: ...


class GeminiProductionPlanner:
    def __init__(self, gateway: GeminiGateway) -> None:
        self._gateway = gateway

    def plan(self, occasion: str, moods: list[str]) -> Storyboard:
        return self._gateway.generate_json(build_storyboard_prompt(occasion, moods), Storyboard)


class GoogleGenAiGateway:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        from google import genai

        resolved_api_key = api_key or os.environ["GEMINI_API_KEY"]
        self._client = genai.Client(api_key=resolved_api_key)
        self._model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    def generate_json(self, prompt: str, schema: type[Storyboard]) -> Storyboard:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        return schema.model_validate_json(response.text)
