import io
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi.responses import StreamingResponse

import app.main as main_module
from app.media_analysis import MediaAnalysis, StoredMedia
from app.render import DeterministicVerticalRenderer, RenderExecutionError, RenderVerificationError
from app.usage_limits import QuotaExceeded


class RenderStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}
        self.decisions: dict[str, tuple[str, str]] = {}

    def put(self, media_id: str, content_type: str, body: bytes) -> StoredMedia:
        self.objects[media_id] = body
        self.content_types[media_id] = content_type
        return StoredMedia(
            media_id=media_id,
            content_type=content_type,
            size_bytes=len(body),
            sha256="digest",
            gs_uri=f"gs://private/media/{media_id}/original",
        )

    def read(self, media_id: str):
        if media_id not in self.objects:
            return None
        return StoredMedia(
            media_id=media_id,
            content_type=self.content_types[media_id],
            size_bytes=len(self.objects[media_id]),
            sha256="digest",
            gs_uri=f"gs://private/media/{media_id}/original",
        ), self.objects[media_id]

    def save_decision(self, state):
        self.decisions[state.media_id] = (state.status, state.reason)
        return state

    def load_decision(self, media_id: str):
        decision = self.decisions.get(media_id)
        if decision is None:
            return None
        from app.media_analysis import MediaDecisionState

        return MediaDecisionState(media_id=media_id, status=decision[0], reason=decision[1])


class RenderAnalyzer:
    def analyze(self, stored_media: StoredMedia) -> MediaAnalysis:
        return MediaAnalysis(
            media_id=stored_media.media_id,
            description="a family moment",
            quality_score=0.9,
            privacy_flags=[],
            orientation="landscape",
            duration_seconds=None,
        )


class RecordingExecutor:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> None:
        self.commands.append(command)
        output = command[-1]
        if output.endswith(".mp4"):
            with open(output, "wb") as video:
                video.write(b"fake-video")
        elif output.endswith(".jpg"):
            with open(output, "wb") as cover:
                cover.write(b"fake-cover")


class RecordingHeifConverter:
    def __init__(self) -> None:
        self.calls = []

    def convert(self, source_path, output_path) -> None:
        self.calls.append((source_path, output_path))
        output_path.write_bytes(b"converted-jpeg")


class RecordingGuardian:
    def __init__(self) -> None:
        self.stages: list[str] = []

    def allow_export(self, *, media_ids, soundtrack_mode, stage) -> None:
        self.stages.append(stage)


class RecordingPublisher:
    def __init__(self) -> None:
        self.events = []

    def publish(self, event) -> None:
        self.events.append(event)


class FailingRenderer:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def render_many(self, request, source_paths, output_directory):
        raise self.error


class DenyingQuotaStore:
    def acquire(self, request):
        raise QuotaExceeded("ip")

    def validate(self, admission_id, request):
        raise QuotaExceeded("ip")


class CapturingQuotaStore:
    def __init__(self) -> None:
        self.request = None

    def acquire(self, request):
        from app.usage_limits import QuotaLease

        self.request = request
        return QuotaLease(lambda: None)

    def validate(self, admission_id, request):
        self.request = request


@pytest.mark.anyio
async def test_export_cors_preflight_allows_the_visitor_header() -> None:
    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.options(
            "/renders/export",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-memory-director-visitor",
            },
        )

    assert response.status_code == 200
    assert "x-memory-director-visitor" in response.headers["access-control-allow-headers"].lower()
    assert "x-memory-director-admission" in response.headers["access-control-allow-headers"].lower()


@pytest.mark.anyio
async def test_media_analysis_rejects_an_invalid_admission_before_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer_calls = 0

    class ForbiddenAnalyzer:
        def analyze(self, stored_media):
            nonlocal analyzer_calls
            analyzer_calls += 1
            raise AssertionError("Gemini must not run without admission")

    monkeypatch.setenv("QUOTA_ENABLED", "true")
    monkeypatch.setattr(main_module, "get_quota_store", lambda: DenyingQuotaStore())
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: ForbiddenAnalyzer())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/analyze",
            headers={"X-Memory-Director-Visitor": "visitor-a", "X-Memory-Director-Admission": "denied"},
            files={"media": ("memory.jpg", b"photo", "image/jpeg")},
            data={"consent": "true"},
        )

    assert response.status_code == 429
    assert analyzer_calls == 0


@pytest.mark.anyio
async def test_export_trusts_forwarded_ip_only_when_proxy_headers_are_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = CapturingQuotaStore()
    async def admitted_export(**kwargs):
        return StreamingResponse(io.BytesIO(b"ok"))

    monkeypatch.setattr(main_module, "get_quota_store", lambda: store)
    monkeypatch.setenv("QUOTA_ENABLED", "true")
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "false")
    monkeypatch.setattr(main_module, "_export_render_admitted", admitted_export)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://direct-client") as client:
        response = await client.post(
            "/renders/export",
            headers={"X-Forwarded-For": "198.51.100.9", "X-Memory-Director-Visitor": "visitor-a", "X-Memory-Director-Admission": "admission-a"},
            data={"title": "A memory", "caption": "Together.", "approved": "true"},
        )

    assert response.status_code == 200
    assert store.request.client_ip == "127.0.0.1"


@pytest.mark.anyio
async def test_export_ignores_a_spoofed_forwarded_prefix_behind_google_load_balancing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = CapturingQuotaStore()

    async def admitted_export(**kwargs):
        return StreamingResponse(io.BytesIO(b"ok"))

    monkeypatch.setattr(main_module, "get_quota_store", lambda: store)
    monkeypatch.setenv("QUOTA_ENABLED", "true")
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    monkeypatch.setattr(main_module, "_export_render_admitted", admitted_export)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/renders/export",
            headers={
                "X-Forwarded-For": "198.51.100.9, 203.0.113.8, 35.191.0.1",
                "X-Memory-Director-Visitor": "visitor-a",
                "X-Memory-Director-Admission": "admission-a",
            },
            data={"title": "A memory", "caption": "Together.", "approved": "true"},
        )

    assert response.status_code == 200
    assert store.request.client_ip == "203.0.113.8"


@pytest.mark.anyio
async def test_selected_analyzed_media_reaches_renderer_without_new_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = RenderStorage()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: RenderAnalyzer(), raising=False)
    monkeypatch.setattr(main_module, "get_renderer", lambda: DeterministicVerticalRenderer(RecordingExecutor()))
    monkeypatch.setattr(main_module, "get_consent_guardian", lambda: RecordingGuardian(), raising=False)
    monkeypatch.setattr(main_module, "get_consent_event_publisher", lambda: RecordingPublisher(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        analyzed = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"render-me", "image/jpeg")},
            data={"consent": "true"},
        )
        media_id = analyzed.json()["media_id"]
        selected = await client.post(
            f"/media/{media_id}/decision",
            json={"status": "selected", "reason": "best frame"},
        )
        exported = await client.post(
            "/renders/export",
            data={"title": "A memory", "caption": "Together.", "approved": "true", "media_id": media_id},
        )

    assert selected.status_code == 200
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as bundle:
        assert any(name.endswith(".mp4") for name in bundle.namelist())
        assert any(name.endswith(".jpg") for name in bundle.namelist())


@pytest.mark.anyio
async def test_selected_heic_media_keeps_its_format_when_staged_for_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = RenderStorage()
    executor = RecordingExecutor()
    converter = RecordingHeifConverter()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: RenderAnalyzer(), raising=False)
    monkeypatch.setattr(
        main_module,
        "get_renderer",
        lambda: DeterministicVerticalRenderer(executor, heif_converter=converter),
    )
    monkeypatch.setattr(main_module, "get_consent_guardian", lambda: RecordingGuardian(), raising=False)
    monkeypatch.setattr(main_module, "get_consent_event_publisher", lambda: RecordingPublisher(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        analyzed = await client.post(
            "/media/analyze",
            files={"media": ("phone-photo.heic", b"synthetic-heic", "image/heic")},
            data={"consent": "true"},
        )
        media_id = analyzed.json()["media_id"]
        await client.post(
            f"/media/{media_id}/decision",
            json={"status": "selected", "reason": "phone photo"},
        )
        exported = await client.post(
            "/renders/export",
            data={"title": "Phone memory", "caption": "Together.", "approved": "true"},
            files=[("media_ids", (None, media_id))],
        )

    assert exported.status_code == 200
    assert converter.calls[0][0].name == "source-0.heic"
    assert any(argument.endswith("converted-source-0.jpg") for argument in executor.commands[0])


@pytest.mark.anyio
@pytest.mark.parametrize(
    "render_error",
    [RenderExecutionError("Video rendering failed."), RenderVerificationError("Video duration could not be verified.")],
)
async def test_render_failure_returns_a_generic_retryable_response(
    monkeypatch: pytest.MonkeyPatch, render_error: Exception
) -> None:
    storage = RenderStorage()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: RenderAnalyzer(), raising=False)
    monkeypatch.setattr(main_module, "get_renderer", lambda: FailingRenderer(render_error))
    monkeypatch.setattr(main_module, "get_consent_guardian", lambda: RecordingGuardian(), raising=False)
    monkeypatch.setattr(main_module, "get_consent_event_publisher", lambda: RecordingPublisher(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        analyzed = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"render-me", "image/jpeg")},
            data={"consent": "true"},
        )
        media_id = analyzed.json()["media_id"]
        await client.post(
            f"/media/{media_id}/decision",
            json={"status": "selected", "reason": "best frame"},
        )
        exported = await client.post(
            "/renders/export",
            data={"title": "A memory", "caption": "Together.", "approved": "true", "media_id": media_id},
        )

    assert exported.status_code == 503
    assert exported.json() == {"detail": "Video rendering is temporarily unavailable; please try again."}


@pytest.mark.anyio
async def test_held_back_analyzed_media_cannot_reach_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = RenderStorage()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: RenderAnalyzer(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        analyzed = await client.post(
            "/media/analyze",
            files={"media": ("held.jpg", b"hold-me", "image/jpeg")},
            data={"consent": "true"},
        )
        media_id = analyzed.json()["media_id"]
        await client.post(
            f"/media/{media_id}/decision",
            json={"status": "held_back", "reason": "duplicate"},
        )
        exported = await client.post(
            "/renders/export",
            data={"title": "A memory", "caption": "Together.", "approved": "true", "media_id": media_id},
        )

    assert exported.status_code == 409


@pytest.mark.anyio
async def test_two_selected_analyzed_media_are_combined_in_one_export(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = RenderStorage()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: RenderAnalyzer(), raising=False)
    executor = RecordingExecutor()
    renderer = DeterministicVerticalRenderer(executor)
    monkeypatch.setattr(main_module, "get_renderer", lambda: renderer)
    guardian = RecordingGuardian()
    monkeypatch.setattr(main_module, "get_consent_guardian", lambda: guardian, raising=False)
    monkeypatch.setattr(main_module, "get_consent_event_publisher", lambda: RecordingPublisher(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        first = await client.post("/media/analyze", files={"media": ("first.jpg", b"first", "image/jpeg")}, data={"consent": "true"})
        second = await client.post("/media/analyze", files={"media": ("second.jpg", b"second", "image/jpeg")}, data={"consent": "true"})
        first_id = first.json()["media_id"]
        second_id = second.json()["media_id"]
        await client.post(f"/media/{first_id}/decision", json={"status": "selected", "reason": "best moment"})
        await client.post(f"/media/{second_id}/decision", json={"status": "selected", "reason": "best moment"})
        exported = await client.post(
            "/renders/export",
            data={"title": "A memory", "caption": "Together.", "approved": "true"},
            files=[("media_ids", (None, first_id)), ("media_ids", (None, second_id))],
        )

    assert exported.status_code == 200
    render_commands = [" ".join(command) for command in executor.commands]
    assert any("fade=t=in" in command and "concat=n=2:v=1:a=0" in command for command in render_commands)
    assert all("xfade=" not in command for command in render_commands)
    assert guardian.stages == ["render", "export"]


@pytest.mark.anyio
async def test_render_quota_rejection_happens_before_renderer_or_lyria(monkeypatch: pytest.MonkeyPatch) -> None:
    renderer_calls = 0
    lyria_calls = 0

    class ForbiddenRenderer:
        def render_many(self, request, source_paths, output_directory):
            nonlocal renderer_calls
            renderer_calls += 1
            raise AssertionError("renderer must not run after quota rejection")

    class ForbiddenLyria:
        def generate(self, prompt: str):
            nonlocal lyria_calls
            lyria_calls += 1
            raise AssertionError("Lyria must not run after quota rejection")

    monkeypatch.setattr(main_module, "get_quota_store", lambda: DenyingQuotaStore(), raising=False)
    monkeypatch.setenv("QUOTA_ENABLED", "true")
    monkeypatch.setattr(main_module, "get_renderer", lambda: ForbiddenRenderer())
    monkeypatch.setattr(main_module, "get_lyria_client", lambda: ForbiddenLyria())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/renders/export",
            headers={"X-Memory-Director-Visitor": "visitor-a", "X-Forwarded-For": "203.0.113.8", "X-Memory-Director-Admission": "denied"},
            files={"media": ("memory.mp4", b"source", "video/mp4")},
            data={
                "title": "Garden day",
                "caption": "Together.",
                "approved": "true",
                "soundtrack_mode": "original_song",
                "memory_details": "Garden",
            },
        )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "86400"
    assert renderer_calls == 0
    assert lyria_calls == 0
