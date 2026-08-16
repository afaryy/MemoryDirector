from app.models import PlaceCandidate, Storyboard
from app.production import ProductionOrchestrator
from tests.test_production import sample_brief


class FakeStoryboardPlanner:
    def plan(self, occasion: str, moods: list[str]) -> Storyboard:
        assert occasion == "Melbourne weekend"
        assert moods == ["cheerful"]
        return Storyboard(title="A Cheerful Melbourne Weekend", caption="A bright weekend together.")


def test_orchestrator_builds_an_explainable_production_proposal() -> None:
    proposal = ProductionOrchestrator(FakeStoryboardPlanner()).produce(
        brief=sample_brief(),
        places=[
            PlaceCandidate(
                label="Eiffel Tower, Paris",
                confidence=0.62,
                evidence=["visual landmark"],
            )
        ],
    )

    assert proposal.storyboard.title == "A Cheerful Melbourne Weekend"
    assert [item.status for item in proposal.curation.items] == ["selected", "held_back"]
    assert proposal.place_confirmation_required is True
    assert len(proposal.music_directions) == 3
    assert proposal.privacy_checks == ["Review visible addresses, dates, and sensitive faces before export."]
