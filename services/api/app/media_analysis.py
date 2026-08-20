import os
from hashlib import sha256
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class StoredMedia(BaseModel):
    media_id: str
    content_type: str
    size_bytes: int = Field(ge=0)
    sha256: str
    gs_uri: str


class MediaAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_id: str
    description: str = Field(min_length=1, max_length=500)
    quality_score: float = Field(ge=0, le=1)
    duplicate_of: str | None = None
    privacy_flags: list[Literal["contains_face", "contains_text", "possible_sensitive_document"]] = Field(
        default_factory=list
    )
    orientation: Literal["portrait", "landscape", "square", "unknown"]
    duration_seconds: float | None = Field(default=None, ge=0)


class MediaAnalyzer(Protocol):
    def analyze(self, stored_media: StoredMedia) -> MediaAnalysis: ...


class MediaAnalysisError(RuntimeError):
    """Raised when the provider cannot return safe, schema-valid analysis."""


def media_id_for_bytes(body: bytes) -> str:
    return f"sha256:{sha256(body).hexdigest()}"


MEDIA_ANALYSIS_PROMPT = """Analyze the attached photo or video for a simple family memory short.
Describe only observable content and return exactly the requested JSON schema.
Use unknown or null when evidence is missing. Do not identify people, infer age,
health, ethnicity, or other sensitive traits. Do not invent a location. Use only
the allow-listed privacy flags and keep the description concise and factual."""


class VertexGeminiMediaAnalyzer:
    def __init__(self, client: Any | None = None, model: str | None = None) -> None:
        if client is None:
            from google import genai

            resolved_api_key = os.environ.get("GEMINI_API_KEY")
            if resolved_api_key:
                client = genai.Client(api_key=resolved_api_key)
            else:
                project = os.environ.get("GOOGLE_CLOUD_PROJECT")
                if not project:
                    raise KeyError("GOOGLE_CLOUD_PROJECT")
                location = os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get(
                    "GEMINI_LOCATION", "us-central1"
                )
                client = genai.Client(vertexai=True, project=project, location=location)
        self._client = client
        self._model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    @classmethod
    def from_environment(cls) -> "VertexGeminiMediaAnalyzer":
        return cls()

    def analyze(self, stored_media: StoredMedia) -> MediaAnalysis:
        try:
            from google.genai import types

            response = self._client.models.generate_content(
                model=self._model,
                contents=[
                    MEDIA_ANALYSIS_PROMPT,
                    types.Part.from_uri(
                        file_uri=stored_media.gs_uri,
                        mime_type=stored_media.content_type,
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MediaAnalysis,
                ),
            )
            analysis = MediaAnalysis.model_validate_json(response.text)
            if analysis.media_id != stored_media.media_id:
                raise ValueError("media ID mismatch")
            return analysis
        except Exception as error:
            if isinstance(error, MediaAnalysisError):
                raise
            raise MediaAnalysisError("media analysis provider failed") from error


class MediaDecisionState(BaseModel):
    media_id: str
    status: Literal["unselected", "selected", "held_back"]
    reason: str = ""


class MediaDecisionRegistry:
    def __init__(self) -> None:
        self._states: dict[str, MediaDecisionState] = {}

    def register(self, media_id: str) -> MediaDecisionState:
        return self._states.setdefault(
            media_id,
            MediaDecisionState(media_id=media_id, status="unselected"),
        )

    def set(self, media_id: str, status: Literal["selected", "held_back"], reason: str) -> MediaDecisionState:
        state = MediaDecisionState(media_id=media_id, status=status, reason=reason)
        self._states[media_id] = state
        return state

    def get(self, media_id: str) -> MediaDecisionState | None:
        return self._states.get(media_id)

