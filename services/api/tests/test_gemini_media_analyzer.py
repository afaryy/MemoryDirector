import json

import pytest

from app.media_analysis import MediaAnalysisError, StoredMedia, VertexGeminiMediaAnalyzer


class RecordingResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class RecordingModels:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.model = None
        self.contents = None
        self.config = None

    def generate_content(self, *, model, contents, config):
        self.model = model
        self.contents = contents
        self.config = config
        return RecordingResponse(self.response_text)


class RecordingGenAiClient:
    def __init__(self, response_text: str) -> None:
        self.models = RecordingModels(response_text)


def stored_media() -> StoredMedia:
    return StoredMedia(
        media_id="sha256:x",
        content_type="image/jpeg",
        size_bytes=3,
        sha256="x",
        gs_uri="gs://private/media/x",
    )


def test_vertex_analyzer_uses_gcs_uri_and_validated_schema() -> None:
    client = RecordingGenAiClient(
        json.dumps(
            {
                "media_id": "sha256:x",
                "description": "a garden",
                "quality_score": 0.9,
                "privacy_flags": [],
                "orientation": "landscape",
                "duration_seconds": None,
            }
        )
    )
    analyzer = VertexGeminiMediaAnalyzer(client=client, model="gemini-test")

    result = analyzer.analyze(stored_media())

    assert result.description == "a garden"
    assert client.models.model == "gemini-test"
    assert client.models.contents[1].file_data.file_uri == "gs://private/media/x"
    assert client.models.contents[1].file_data.mime_type == "image/jpeg"
    assert client.models.config.response_mime_type == "application/json"
    assert client.models.config.response_schema is not None


def test_vertex_analyzer_rejects_provider_json_with_wrong_media_id() -> None:
    client = RecordingGenAiClient(
        '{"media_id":"sha256:other","description":"a garden","quality_score":0.9,"privacy_flags":[],"orientation":"landscape","duration_seconds":null}'
    )

    with pytest.raises(MediaAnalysisError):
        VertexGeminiMediaAnalyzer(client=client).analyze(stored_media())
