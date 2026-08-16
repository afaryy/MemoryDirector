from app.gemini_client import GeminiProductionPlanner
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
