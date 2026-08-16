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
from app.models import PlaceCandidate, ProductionBrief, ProductionProposal, Storyboard
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


class ProductionProposalPayload(BaseModel):
    brief: ProductionBrief
    places: list[PlaceCandidate]


MAX_UPLOAD_BYTES = 50 * 1024 * 1024


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    media: UploadFile = File(...),
) -> StreamingResponse:
    """Render one approved upload and return MP4, cover, and caption as a zip."""
    if not approved:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approve the plan before creating a video.")
    if not media.content_type or not (media.content_type.startswith("video/") or media.content_type.startswith("image/")):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a video or image file.")

    contents = await media.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Media upload is limited to 50 MB.")

    suffix = Path(media.filename or "upload.mp4").suffix.lower()
    if suffix not in {".mp4", ".mov", ".m4v", ".webm", ".jpg", ".jpeg", ".png"}:
        suffix = ".mp4"

    with tempfile.TemporaryDirectory(prefix="memory-director-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        source_path = temporary_root / f"source{suffix}"
        source_path.write_bytes(contents)
        output_directory = temporary_root / "exports"
        artifact = get_renderer().render(
            RenderRequest(title=title, caption=caption),
            source_path,
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


@app.post("/storyboards", response_model=Storyboard, status_code=status.HTTP_201_CREATED)
def create_storyboard(
    payload: StoryboardPayload,
) -> Storyboard:
    return get_production_planner().plan(payload.occasion, payload.moods)


@app.post("/production-proposals", response_model=ProductionProposal, status_code=status.HTTP_201_CREATED)
def create_production_proposal(payload: ProductionProposalPayload) -> ProductionProposal:
    return ProductionOrchestrator(get_production_planner()).produce(payload.brief, payload.places)
