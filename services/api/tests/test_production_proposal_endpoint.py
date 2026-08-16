import app.main as main_module
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import Storyboard


class FakePlanner:
    def plan(self, occasion: str, moods: list[str]) -> Storyboard:
        return Storyboard(title="A Cheerful Melbourne Weekend", caption="A bright weekend together.")


@pytest.mark.anyio
async def test_production_proposal_endpoint_combines_gemini_and_safe_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "get_production_planner", lambda: FakePlanner())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/production-proposals",
            json={
                "brief": {
                    "occasion": "Melbourne weekend",
                    "target_duration_seconds": 45,
                    "moods": ["cheerful"],
                    "music_constraints": ["gentle"],
                    "media": [
                        {"media_id": "clip-1", "quality_score": 0.95, "duplicate_of": None},
                        {"media_id": "clip-2", "quality_score": 0.2, "duplicate_of": "clip-1"},
                    ],
                },
                "places": [
                    {"label": "Eiffel Tower, Paris", "confidence": 0.62, "evidence": ["visual landmark"]}
                ],
            },
        )

    assert response.status_code == 201
    assert response.json()["place_confirmation_required"] is True
    assert response.json()["curation"]["items"][1]["status"] == "held_back"
    assert response.json()["storyboard"]["title"] == "A Cheerful Melbourne Weekend"
