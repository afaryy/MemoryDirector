import os
import io
import tempfile
import zipfile
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.gemini_client import GeminiProductionPlanner, GoogleGenAiGateway
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
from app.models import PlaceCandidate, ProductionBrief, ProductionProposal, Storyboard
from app.preferences import preference_repository_from_environment
from app.production import ProductionOrchestrator
from app.render import (
    ApprovalRequired,
    DeterministicVerticalRenderer,
    RenderRequest,
    SubprocessRenderExecutor,
    create_render_request,
)

app = FastAPI(title="Memory Director API")
allowed_origins = [origin.strip() for origin in os.environ.get("WEB_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
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
    brief: ProductionBrief
    places: list[PlaceCandidate]


class MediaAnalysisResponse(MediaAnalysis):
    decision_status: Literal["unselected", "selected", "held_back"]


class MediaDecisionPayload(BaseModel):
    status: Literal["selected", "held_back"]
    reason: str = Field(min_length=1, max_length=500)


MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_media_decisions = MediaDecisionRegistry()


def get_production_planner() -> GeminiProductionPlanner:
    try:
        return GeminiProductionPlanner(GoogleGenAiGateway())
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini production planning is not configured.",
        ) from error


def get_renderer() -> DeterministicVerticalRenderer:
    return DeterministicVerticalRenderer(SubprocessRenderExecutor())


def get_preference_repository():
    return preference_repository_from_environment()


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


def _contains_private_uri(analysis: MediaAnalysis) -> bool:
    return "gs://" in analysis.model_dump_json()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/media/analyze", response_model=MediaAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def analyze_media(
    consent: str = Form(...),
    media: UploadFile = File(...),
) -> MediaAnalysisResponse:
    if consent != "true":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Explicit media consent is required.")
    if not media.content_type or not (
        media.content_type.startswith("video/") or media.content_type.startswith("image/")
    ):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a photo or video file.")

    contents = await media.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Media upload is limited to 50 MB.")

    media_id = media_id_for_bytes(contents)
    try:
        storage = get_media_storage()
        stored_media = storage.put(media_id, media.content_type, contents)
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
        return storage.save_decision(state)
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Media decision is temporarily unavailable.") from error


@app.post("/renders", response_model=RenderRequest, status_code=status.HTTP_201_CREATED)
def request_render(payload: RenderPayload) -> RenderRequest:
    try:
        return create_render_request(payload.storyboard, payload.approved)
    except ApprovalRequired as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.post("/renders/export", status_code=status.HTTP_200_OK)
async def export_render(
    title: str = Form(..., min_length=1, max_length=120),
    caption: str = Form(..., min_length=1, max_length=500),
    approved: bool = Form(...),
    media: UploadFile | None = File(None),
    media_id: str | None = Form(None),
    media_ids: list[str] | None = Form(None),
) -> StreamingResponse:
    """Render approved media and return an MP4, cover, and caption as a zip."""
    if not approved:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approve the plan before creating a video.")
    requested_media_ids = list(media_ids or [])
    if media_id is not None:
        requested_media_ids.insert(0, media_id)
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
            stored = storage.read(requested_id)
            if stored is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset is unavailable.")
            stored_media, contents = stored
            selected_sources.append((contents, ".mp4" if stored_media.content_type.startswith("video/") else ".jpg"))
        source_contents = selected_sources
    else:
        if media is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Upload media or provide selected media_ids.")
        if not media.content_type or not (media.content_type.startswith("video/") or media.content_type.startswith("image/")):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a video or image file.")

        contents = await media.read(MAX_UPLOAD_BYTES + 1)
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Media upload is limited to 50 MB.")

        suffix = Path(media.filename or "upload.mp4").suffix.lower()
        if suffix not in {".mp4", ".mov", ".m4v", ".webm", ".jpg", ".jpeg", ".png"}:
            suffix = ".mp4"
        source_contents = [(contents, suffix)]

    with tempfile.TemporaryDirectory(prefix="memory-director-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        source_paths: list[Path] = []
        for index, (source_bytes, suffix) in enumerate(source_contents):
            source_path = temporary_root / f"source-{index}{suffix}"
            source_path.write_bytes(source_bytes)
            source_paths.append(source_path)
        output_directory = temporary_root / "exports"
        artifact = get_renderer().render_many(
            RenderRequest(title=title, caption=caption),
            source_paths,
            output_directory,
        )

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
) -> Storyboard:
    storyboard = get_production_planner().plan(payload.occasion, payload.moods)
    repository = get_preference_repository()
    if repository is None:
        return storyboard
    try:
        recommendation = repository.recommend(payload.user_id, payload.occasion)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Preference memory is temporarily unavailable.",
        ) from error
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
def create_production_proposal(payload: ProductionProposalPayload) -> ProductionProposal:
    return ProductionOrchestrator(get_production_planner()).produce(payload.brief, payload.places)
