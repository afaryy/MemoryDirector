import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_render_endpoint_rejects_unapproved_storyboard() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/renders",
            json={
                "storyboard": {"title": "Weekend by the sea", "caption": "A gentle escape."},
                "approved": False,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Approve the plan before creating a video."


@pytest.mark.anyio
async def test_render_endpoint_returns_share_ready_request_after_approval() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/renders",
            json={
                "storyboard": {"title": "Weekend by the sea", "caption": "A gentle escape."},
                "approved": True,
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "title": "Weekend by the sea",
        "caption": "A gentle escape.",
        "output_format": "vertical-mp4",
    }
