import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.main import app
from app.models import Storyboard
from app.preferences import PreferenceRecommendation


class FakePlanner:
    def plan(self, occasion: str, moods: list[str]) -> Storyboard:
        assert occasion == "A family day by the sea"
        assert moods == ["warm", "cheerful"]
        return Storyboard(title="A Family Day by the Sea", caption="Small moments, held close.")


@pytest.mark.anyio
async def test_storyboard_endpoint_uses_configured_production_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module, "get_production_planner", lambda: FakePlanner())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/storyboards",
            json={
                "occasion": "A family day by the sea",
                "moods": ["warm", "cheerful"],
                "media_count": 3,
                "media_consent": True,
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "title": "A Family Day by the Sea",
        "caption": "Small moments, held close.",
    }


@pytest.mark.anyio
async def test_storyboard_endpoint_requires_explicit_media_consent() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/storyboards",
            json={
                "occasion": "A family day by the sea",
                "moods": ["warm"],
                "media_count": 3,
                "media_consent": False,
            },
        )

    assert response.status_code == 422


class FakePreferenceRepository:
    def recommend(self, user_id: str, occasion: str) -> PreferenceRecommendation:
        assert user_id == "demo-user"
        assert occasion == "A family day by the sea"
        return PreferenceRecommendation(
            music_direction="gentle festive instrumental",
            evidence_count=2,
            explanation="You chose gentle festive twice before for similar memories.",
        )


@pytest.mark.anyio
async def test_storyboard_endpoint_surfaces_clickhouse_preference_explanation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "get_production_planner", lambda: FakePlanner())
    monkeypatch.setattr(main_module, "get_preference_repository", lambda: FakePreferenceRepository())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/storyboards",
            json={
                "occasion": "A family day by the sea",
                "moods": ["warm", "cheerful"],
                "media_count": 3,
                "media_consent": True,
                "user_id": "demo-user",
            },
        )

    assert response.status_code == 201
    assert response.json()["music_direction"] == "gentle festive instrumental"
    assert response.json()["preference_explanation"].startswith("You chose gentle festive")
