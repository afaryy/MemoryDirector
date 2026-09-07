import os
import io
import base64
import logging
import tempfile
import zipfile
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from app.agent_engine import AgentEnginePlanner, AgentPlannerUnavailable
from app.agent_planner import AgentPlanAdapter, AgentPlanningRequest
from app.gemini_client import GeminiProductionPlanner, GoogleGenAiGateway
from app.consent_guardian import ConsentDenied, consent_guardian_from_environment
from app.consent_events import ConsentEvent, consent_event_publisher_from_environment
from app.media_analysis import (
    MediaAnalysis,
    MediaAnalysisError,
    MediaDecisionRegistry,
    MediaDecisionState,
    VertexGeminiMediaAnalyzer,
    ensure_safe_media_analysis,
    media_id_for_bytes,
)
from app.media_storage import GcsMediaStorage, MediaStorage
from app.memory_song import UnsafeSongRequest, build_memory_song_brief
from app.lyria_client import GoogleLyriaClient
from app.models import PlaceCandidate, ProductionBrief, ProductionProposal, Storyboard
from app.preferences import preference_repository_from_environment
from app.production import ProductionOrchestrator
from app.soundtrack import SoundtrackConfigurationError, resolve_instrumental_track
from app.usage_limits import AdmissionStage, QuotaExceeded, QuotaRequest, QuotaStore, quota_store_from_environment
from app.render import (
    ApprovalRequired,
    DeterministicVerticalRenderer,
    RenderExecutionError,
    RenderRequest,
    RenderVerificationError,
    SubprocessHeifConverter,
    SubprocessRenderExecutor,
    SubprocessVideoDurationProbe,
    create_render_request,
)

app = FastAPI(title="Memory Director API")
logger = logging.getLogger(__name__)
allowed_origins = [origin.strip() for origin in os.environ.get("WEB_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST"],
    allow_headers=["Content-Type", "X-Memory-Director-Visitor", "X-Memory-Director-Admission"],
)


class RenderPayload(BaseModel):
    storyboard: Storyboard
    approved: bool


class StoryboardPayload(BaseModel):
    occasion: str
    moods: list[str]
    media_count: int = Field(gt=0)
    media_consent: Literal[True]
    user_id: str = Field(default="demo-user", min_length=1, max_length=120)


class ProductionProposalPayload(BaseModel):
    user_id: str = Field(default="demo-user", min_length=1, max_length=128)
    brief: ProductionBrief
    places: list[PlaceCandidate]


class MediaAnalysisResponse(MediaAnalysis):
    decision_status: Literal["unselected", "selected", "held_back"]


class MediaDecisionPayload(BaseModel):
    status: Literal["selected", "held_back"]
    reason: str = Field(min_length=1, max_length=500)


class MemorySongBriefPayload(BaseModel):
    memory_details: list[str] = Field(min_length=1, max_length=12)
    requested_style: str = Field(default="warm acoustic", max_length=300)


class AdmissionPayload(BaseModel):
    soundtrack_mode: Literal["original_song", "instrumental", "no_sound"]


def configured_positive_integer(name: str, default: int) -> int:
    value = int(os.environ.get(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def max_upload_bytes() -> int:
    return configured_positive_integer("MAX_UPLOAD_FILE_MB", 50) * 1024 * 1024


def max_media_items() -> int:
    return configured_positive_integer("MAX_MEDIA_ITEMS", 15)


def max_request_text_chars() -> int:
    return configured_positive_integer("MAX_REQUEST_TEXT_CHARS", 2000)
MEDIA_SUFFIX_BY_CONTENT_TYPE = {
    "image/heic": ".heic",
    "image/heic-sequence": ".heic",
    "image/heif": ".heif",
    "image/heif-sequence": ".heif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-m4v": ".m4v",
}
_media_decisions = MediaDecisionRegistry()


def normalize_media_content_type(content_type: str | None) -> str:
    return (content_type or "").partition(";")[0].strip().lower()


def media_suffix_for_content_type(content_type: str) -> str:
    normalized = normalize_media_content_type(content_type)
    mapped = MEDIA_SUFFIX_BY_CONTENT_TYPE.get(normalized)
    if mapped is not None:
        return mapped
    return ".mp4" if normalized.startswith("video/") else ".jpg"


def get_production_planner() -> GeminiProductionPlanner:
    try:
        return GeminiProductionPlanner(GoogleGenAiGateway())
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini production planning is not configured.",
        ) from error


def get_agent_planner() -> AgentEnginePlanner | None:
    if not os.environ.get("MEMORY_FILM_PLANNER_RESOURCE"):
        return None
    try:
        return AgentEnginePlanner.from_environment()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent Engine production planning is not configured.",
        ) from error


def get_renderer() -> DeterministicVerticalRenderer:
    return DeterministicVerticalRenderer(
        SubprocessRenderExecutor(),
        duration_probe=SubprocessVideoDurationProbe(),
        heif_converter=SubprocessHeifConverter(),
    )


def get_preference_repository():
    return preference_repository_from_environment()


def get_consent_guardian():
    return consent_guardian_from_environment()


def get_consent_event_publisher():
    return consent_event_publisher_from_environment()


def get_media_storage() -> MediaStorage:
    try:
        return GcsMediaStorage.from_environment()
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media storage is not configured.",
        ) from error


def get_media_analyzer() -> VertexGeminiMediaAnalyzer:
    try:
        return VertexGeminiMediaAnalyzer.from_environment()
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media analysis is not configured.",
        ) from error


def get_lyria_client() -> GoogleLyriaClient:
    return GoogleLyriaClient()


@lru_cache(maxsize=1)
def get_quota_store() -> QuotaStore:
    return quota_store_from_environment()


def quota_request_from_http(request: Request, *, includes_original_song: bool) -> QuotaRequest:
    trust_proxy_headers = os.environ.get("TRUST_PROXY_HEADERS", "false").lower() == "true"
    forwarded_values = [value.strip() for value in request.headers.get("x-forwarded-for", "").split(",") if value.strip()]
    forwarded_for = forwarded_values[-2] if trust_proxy_headers and len(forwarded_values) >= 2 else ""
    client_ip = forwarded_for or (request.client.host if request.client else "unknown")
    visitor_id = request.headers.get("x-memory-director-visitor", "").strip()
    if not visitor_id or len(visitor_id) > 128:
        user_agent = request.headers.get("user-agent", "unknown")
        visitor_id = sha256(f"{client_ip}\0{user_agent}".encode()).hexdigest()
    return QuotaRequest(
        visitor_id=visitor_id,
        client_ip=client_ip,
        includes_original_song=includes_original_song,
    )


def acquire_quota(request: Request, *, includes_original_song: bool):
    try:
        return get_quota_store().acquire(
            quota_request_from_http(request, includes_original_song=includes_original_song)
        )
    except QuotaExceeded as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(error),
            headers={"Retry-After": "86400"},
        ) from error


def require_admission(
    request: Request,
    stage: AdmissionStage,
    *,
    includes_original_song: bool = False,
) -> str | None:
    if os.environ.get("QUOTA_ENABLED", "false").lower() != "true":
        return None
    admission_id = request.headers.get("x-memory-director-admission", "").strip()
    if not admission_id:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Start a new film request and try again.", headers={"Retry-After": "60"})
    try:
        get_quota_store().consume(
            admission_id,
            quota_request_from_http(request, includes_original_song=includes_original_song),
            stage,
        )
    except QuotaExceeded as error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(error), headers={"Retry-After": "86400"}) from error
    return admission_id


@app.post("/usage/admissions", status_code=status.HTTP_201_CREATED)
def create_usage_admission(payload: AdmissionPayload, request: Request) -> dict[str, str]:
    lease = acquire_quota(request, includes_original_song=payload.soundtrack_mode == "original_song")
    return {"admission_id": lease.admission_id or "quota-disabled"}


@app.post("/usage/admissions/{admission_id}/release", status_code=status.HTTP_204_NO_CONTENT)
def release_usage_admission(admission_id: str, request: Request) -> None:
    if os.environ.get("QUOTA_ENABLED", "false").lower() != "true":
        return
    get_quota_store().validate(admission_id, quota_request_from_http(request, includes_original_song=False))
    get_quota_store().release(admission_id)


@app.post("/memory-songs/brief", status_code=status.HTTP_201_CREATED)
def create_memory_song_brief(payload: MemorySongBriefPayload) -> dict[str, str]:
    try:
        brief = build_memory_song_brief(
            memory_details=payload.memory_details,
            requested_style=payload.requested_style,
        )
    except UnsafeSongRequest as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return {"prompt": brief.prompt, "fallback": brief.fallback}


@app.post("/memory-songs", status_code=status.HTTP_201_CREATED)
def generate_memory_song(payload: MemorySongBriefPayload, request: Request) -> dict[str, str]:
    try:
        brief = build_memory_song_brief(memory_details=payload.memory_details, requested_style=payload.requested_style)
    except UnsafeSongRequest as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    require_admission(request, "song", includes_original_song=True)
    try:
        song = get_lyria_client().generate(brief.prompt)
    except (KeyError, RuntimeError) as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Original song is unavailable; choose instrumental or no sound.") from error
    return {"audio_base64": base64.b64encode(song.audio).decode(), "lyrics": song.lyrics, "model": song.model, "fallback": brief.fallback}


def _contains_private_uri(analysis: MediaAnalysis) -> bool:
    return "gs://" in analysis.model_dump_json()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/media/analyze", response_model=MediaAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def analyze_media(
    request: Request,
    consent: str = Form(...),
    media: UploadFile = File(...),
) -> MediaAnalysisResponse:
    if consent != "true":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Explicit media consent is required.")
    normalized_content_type = normalize_media_content_type(media.content_type)
    if not (normalized_content_type.startswith("video/") or normalized_content_type.startswith("image/")):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a photo or video file.")

    upload_limit = max_upload_bytes()
    contents = await media.read(upload_limit + 1)
    if len(contents) > upload_limit:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="That file is too large to use.")

    require_admission(request, "media_analysis")

    media_id = media_id_for_bytes(contents)
    try:
        storage = get_media_storage()
        stored_media = storage.put(media_id, normalized_content_type, contents)
        analysis = get_media_analyzer().analyze(stored_media)
        if analysis.media_id != media_id:
            raise MediaAnalysisError("media ID mismatch")
        analysis = ensure_safe_media_analysis(analysis)
        persisted = storage.load_decision(media_id)
        decision = _media_decisions.remember(persisted) if persisted else _media_decisions.register(media_id)
        storage.save_decision(decision)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Media analysis is temporarily unavailable.") from error

    return MediaAnalysisResponse(**analysis.model_dump(), decision_status=decision.status)


@app.post("/media/{media_id}/decision", response_model=MediaDecisionState, status_code=status.HTTP_200_OK)
def decide_media(media_id: str, payload: MediaDecisionPayload) -> MediaDecisionState:
    storage = get_media_storage()
    persisted = storage.load_decision(media_id)
    current = persisted or _media_decisions.get(media_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset was not analyzed.")
    state = _media_decisions.set(media_id, payload.status, payload.reason)
    try:
        saved = storage.save_decision(state)
        if saved.status == "selected":
            publisher = get_consent_event_publisher()
            if publisher is None:
                raise RuntimeError("consent event writer is not configured")
            publisher.publish(ConsentEvent(session_id=media_id, media_id=media_id, event_type="media_selected"))
        return saved
    except Exception as error:
        logger.warning("Media decision or consent publication failed: %s", type(error).__name__)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Media decision is temporarily unavailable.") from error


@app.post(
    "/renders",
    response_model=RenderRequest,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def request_render(payload: RenderPayload) -> RenderRequest:
    try:
        return create_render_request(payload.storyboard, payload.approved)
    except ApprovalRequired as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.post("/renders/export", status_code=status.HTTP_200_OK)
async def export_render(
    request: Request,
    title: str = Form(..., min_length=1, max_length=120),
    caption: str = Form(..., min_length=1, max_length=500),
    approved: bool = Form(...),
    soundtrack_mode: Literal["original_song", "instrumental", "no_sound"] = Form("no_sound"),
    memory_details: list[str] | None = Form(None),
    requested_style: str = Form("warm acoustic", max_length=300),
    media: UploadFile | None = File(None),
    media_id: str | None = Form(None),
    media_ids: list[str] | None = Form(None),
) -> StreamingResponse:
    require_admission(request, "export", includes_original_song=soundtrack_mode == "original_song")
    return await _export_render_admitted(
        title=title,
        caption=caption,
        approved=approved,
        soundtrack_mode=soundtrack_mode,
        memory_details=memory_details,
        requested_style=requested_style,
        media=media,
        media_id=media_id,
        media_ids=media_ids,
    )


async def _export_render_admitted(
    *,
    title: str,
    caption: str,
    approved: bool,
    soundtrack_mode: Literal["original_song", "instrumental", "no_sound"],
    memory_details: list[str] | None,
    requested_style: str,
    media: UploadFile | None,
    media_id: str | None,
    media_ids: list[str] | None,
) -> StreamingResponse:
    """Render approved media and return an MP4, cover, and caption as a zip."""
    if not approved:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approve the plan before creating a video.")
    requested_media_ids = list(media_ids or [])
    if media_id is not None:
        requested_media_ids.insert(0, media_id)
    if len(requested_media_ids) > max_media_items():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choose fewer photos and videos.")
    if requested_media_ids:
        if media is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choose media upload or media_ids, not both.")
        selected_sources: list[tuple[bytes, str]] = []
        storage = get_media_storage()
        for requested_id in requested_media_ids:
            persisted = storage.load_decision(requested_id)
            decision = persisted or _media_decisions.get(requested_id)
            if decision is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset was not analyzed.")
            if decision.status != "selected":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Select the media asset before rendering.")
        guardian = get_consent_guardian()
        if guardian is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Consent evidence is unavailable; please try again later.")
        try:
            guardian.allow_export(media_ids=requested_media_ids, soundtrack_mode=soundtrack_mode, stage="render")
        except ConsentDenied as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        publisher = get_consent_event_publisher()
        if publisher is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Consent event recording is unavailable.")
        try:
            for requested_id in requested_media_ids:
                publisher.publish(ConsentEvent(session_id=requested_id, media_id=requested_id, event_type="render_started"))
        except Exception as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Consent event recording is unavailable.") from error
        for requested_id in requested_media_ids:
            stored = storage.read(requested_id)
            if stored is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset is unavailable.")
            stored_media, contents = stored
            selected_sources.append((contents, media_suffix_for_content_type(stored_media.content_type)))
        source_contents = selected_sources
    else:
        if media is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Upload media or provide selected media_ids.")
        normalized_content_type = normalize_media_content_type(media.content_type)
        if not (normalized_content_type.startswith("video/") or normalized_content_type.startswith("image/")):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a video or image file.")

        upload_limit = max_upload_bytes()
        contents = await media.read(upload_limit + 1)
        if len(contents) > upload_limit:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="That file is too large to use.")

        suffix = Path(media.filename or "upload.mp4").suffix.lower()
        canonical_suffix = MEDIA_SUFFIX_BY_CONTENT_TYPE.get(normalized_content_type)
        if canonical_suffix is not None:
            suffix = canonical_suffix
        elif suffix not in {".mp4", ".mov", ".m4v", ".webm", ".jpg", ".jpeg", ".png", ".heic", ".heif"}:
            suffix = media_suffix_for_content_type(media.content_type)
        source_contents = [(contents, suffix)]

    with tempfile.TemporaryDirectory(prefix="memory-director-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        source_paths: list[Path] = []
        for index, (source_bytes, suffix) in enumerate(source_contents):
            source_path = temporary_root / f"source-{index}{suffix}"
            source_path.write_bytes(source_bytes)
            source_paths.append(source_path)
        audio_path: Path | None = None
        if soundtrack_mode == "original_song":
            try:
                brief = build_memory_song_brief(
                    memory_details=memory_details or [],
                    requested_style=requested_style,
                )
                song = get_lyria_client().generate(brief.prompt)
            except UnsafeSongRequest as error:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
            except (KeyError, RuntimeError) as error:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Original song is unavailable; choose instrumental or no sound.",
                ) from error
            audio_path = temporary_root / "memory-song.mp3"
            audio_path.write_bytes(song.audio)
        elif soundtrack_mode == "instrumental":
            try:
                audio_path = resolve_instrumental_track()
            except SoundtrackConfigurationError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Instrumental music is not configured; choose original song or no sound.",
                ) from error
        output_directory = temporary_root / "exports"
        try:
            artifact = get_renderer().render_many(
                RenderRequest(title=title, caption=caption, audio_path=audio_path),
                source_paths,
                output_directory,
            )
        except (RenderExecutionError, RenderVerificationError) as error:
            logger.warning("Video rendering failed: %s", type(error).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Video rendering is temporarily unavailable; please try again.",
            ) from None

        if requested_media_ids:
            try:
                guardian.allow_export(media_ids=requested_media_ids, soundtrack_mode=soundtrack_mode, stage="export")
            except ConsentDenied as error:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
            try:
                for requested_id in requested_media_ids:
                    publisher.publish(ConsentEvent(session_id=requested_id, media_id=requested_id, event_type="export_completed"))
            except Exception as error:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Consent event recording is unavailable.") from error

        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in (artifact.video_path, artifact.cover_path, artifact.caption_path):
                bundle.write(path, arcname=path.name)
        archive.seek(0)

    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="memory-director-{artifact.render_id}.zip"'},
    )


@app.post(
    "/storyboards",
    response_model=Storyboard,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create_storyboard(
    payload: StoryboardPayload,
    request: Request,
) -> Storyboard:
    if len(payload.occasion) > max_request_text_chars() or payload.media_count > max_media_items():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Shorten the request or choose fewer moments.")
    require_admission(request, "planning")
    storyboard = get_production_planner().plan(payload.occasion, payload.moods)
    try:
        repository = get_preference_repository()
        if repository is None:
            return storyboard
        recommendation = repository.recommend(payload.user_id, payload.occasion)
    except Exception:
        logger.warning("Preference memory unavailable; continuing with the base storyboard", exc_info=True)
        return storyboard
    if recommendation is None:
        return storyboard
    return storyboard.model_copy(
        update={
            "music_direction": recommendation.music_direction,
            "preference_explanation": recommendation.explanation,
            "preference_evidence_count": recommendation.evidence_count,
        }
    )


@app.post("/production-proposals", response_model=ProductionProposal, status_code=status.HTTP_201_CREATED)
def create_production_proposal(payload: ProductionProposalPayload, request: Request) -> ProductionProposal:
    agent_planner = get_agent_planner()
    if agent_planner is None:
        require_admission(request, "planning")
        return ProductionOrchestrator(get_production_planner()).produce(payload.brief, payload.places)

    try:
        planning_request = AgentPlanningRequest.from_brief(
            payload.brief, user_id=payload.user_id
        )
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Production request is outside the bounded agent contract.",
        ) from error
    require_admission(request, "planning")
    try:
        plan = agent_planner.plan(planning_request)
        return AgentPlanAdapter.to_proposal(planning_request, plan)
    except AgentPlannerUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Production planning is temporarily unavailable.",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent Engine returned an invalid production plan.",
        ) from error
