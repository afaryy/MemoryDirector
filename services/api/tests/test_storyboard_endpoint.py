import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app, get_production_planner
from app.models import Storyboard


class FakePlanner:
    def plan(self, occasion: str, moods: list[str]) -> Storyboard:
        assert occasion == "A family day by the sea"
        assert moods == ["warm", "cheerful"]
        return Storyboard(title="A Family Day by the Sea", caption="Small moments, held close.")


@pytest.mark.anyio
async def test_storyboard_endpoint_uses_configured_production_planner() -> None:
    app.dependency_overrides[get_production_planner] = lambda: FakePlanner()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/storyboards",
                json={"occasion": "A family day by the sea", "moods": ["warm", "cheerful"]},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json() == {
        "title": "A Family Day by the Sea",
        "caption": "Small moments, held close.",
    }
