import sys
import types

from app.gemini_client import GeminiProductionPlanner
from app.gemini_client import GoogleGenAiGateway
from app.models import Storyboard


class FakeGeminiGateway:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate_json(self, prompt: str, schema: type[Storyboard]) -> Storyboard:
        self.prompts.append(prompt)
        return Storyboard(title="A Cheerful Melbourne Weekend", caption="A bright weekend together.")


def test_planner_uses_gateway_response_without_network() -> None:
    gateway = FakeGeminiGateway()
    planner = GeminiProductionPlanner(gateway)

    storyboard = planner.plan("Melbourne weekend", ["cheerful"])

    assert storyboard.title == "A Cheerful Melbourne Weekend"
    assert gateway.prompts[0].startswith("You are Memory Director")
    assert "instrumental music direction" in gateway.prompts[0]
    assert "copyrighted recording" in gateway.prompts[0]


def test_gateway_uses_vertex_ai_adc_without_api_key(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            calls.update(kwargs)

    fake_google = types.ModuleType("google")
    fake_google.genai = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    monkeypatch.delenv("GEMINI_LOCATION", raising=False)

    GoogleGenAiGateway(model="gemini-test")

    assert calls == {
        "vertexai": True,
        "project": "demo-project",
        "location": "us-central1",
    }
