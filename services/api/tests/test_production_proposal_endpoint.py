import app.main as main_module
import pytest
from httpx import ASGITransport, AsyncClient

from app.agent_engine import AgentPlannerUnavailable
from app.agent_planner import AgentProductionPlan, SelectedSegment
from app.main import app
from app.models import Storyboard


class FakePlanner:
    def plan(self, occasion: str, moods: list[str]) -> Storyboard:
        return Storyboard(title="A Cheerful Melbourne Weekend", caption="A bright weekend together.")


class FakeAgentPlanner:
    def __init__(self) -> None:
        self.requests = []

    def plan(self, request):
        self.requests.append(request)
        return AgentProductionPlan(
            title="A sunny afternoon",
            caption="A small day worth keeping.",
            music_direction="warm acoustic instrumental",
            selected_segments=[
                SelectedSegment(media_id="clip-1", trim_start_seconds=0, trim_end_seconds=60)
            ],
            held_back_media_ids=["clip-2"],
            user_explanation="I kept the clearest moment.",
        )


class UnavailableAgentPlanner:
    def plan(self, request):
        raise AgentPlannerUnavailable("Agent Engine planning is unavailable.")


def proposal_payload() -> dict:
    return {
        "user_id": "family-7",
        "brief": {
            "occasion": "Melbourne weekend",
            "target_duration_seconds": 60,
            "moods": ["cheerful"],
            "music_constraints": ["gentle"],
            "media": [
                {"media_id": "clip-1", "quality_score": 0.95, "duplicate_of": None},
                {"media_id": "clip-2", "quality_score": 0.2, "duplicate_of": "clip-1"},
            ],
        },
        "places": [],
    }


@pytest.mark.anyio
async def test_production_proposal_endpoint_combines_gemini_and_safe_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "get_agent_planner", lambda: None)
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


@pytest.mark.anyio
async def test_production_proposal_endpoint_uses_configured_agent_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner = FakeAgentPlanner()
    monkeypatch.setattr(main_module, "get_agent_planner", lambda: planner)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/production-proposals", json=proposal_payload())

    assert response.status_code == 201
    assert response.json()["storyboard"]["title"] == "A sunny afternoon"
    assert response.json()["selected_segments"] == [
        {"media_id": "clip-1", "trim_start_seconds": 0.0, "trim_end_seconds": 60.0}
    ]
    assert planner.requests[0].user_id == "family-7"


@pytest.mark.anyio
async def test_production_proposal_endpoint_does_not_fabricate_when_agent_engine_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "get_agent_planner", lambda: UnavailableAgentPlanner())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/production-proposals", json=proposal_payload())

    assert response.status_code == 503
    assert response.json() == {"detail": "Production planning is temporarily unavailable."}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "brief_update",
    [
        {"target_duration_seconds": 45},
        {"occasion": "x" * 501},
        {
            "media": [
                {"media_id": "data:video/mp4;base64,AAAA", "quality_score": 0.9, "duplicate_of": None}
            ]
        },
    ],
)
async def test_configured_agent_rejects_request_outside_bounded_contract(
    monkeypatch: pytest.MonkeyPatch, brief_update: dict
) -> None:
    planner = FakeAgentPlanner()
    monkeypatch.setattr(main_module, "get_agent_planner", lambda: planner)
    payload = proposal_payload()
    payload["brief"].update(brief_update)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/production-proposals", json=payload)

    assert response.status_code == 422
    assert planner.requests == []


@pytest.mark.anyio
async def test_production_proposal_quota_rejection_does_not_call_a_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner = FakeAgentPlanner()

    class DenyingQuotaStore:
        def consume(self, admission_id, request, stage):
            from app.usage_limits import QuotaExceeded

            raise QuotaExceeded("admission")

    monkeypatch.setattr(main_module, "get_agent_planner", lambda: planner)
    monkeypatch.setattr(main_module, "get_quota_store", lambda: DenyingQuotaStore())
    monkeypatch.setenv("QUOTA_ENABLED", "true")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/production-proposals",
            headers={"X-Memory-Director-Admission": "denied"},
            json=proposal_payload(),
        )

    assert response.status_code == 429
    assert planner.requests == []
