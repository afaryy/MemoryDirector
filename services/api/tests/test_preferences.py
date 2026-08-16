from app.preferences import FakePreferenceRepository


def test_recommendation_explains_user_history() -> None:
    repository = FakePreferenceRepository(
        ["gentle festive", "gentle festive", "loud pop rejected"]
    )

    recommendation = repository.recommend("demo-user", "travel")

    assert recommendation.music_direction == "gentle festive instrumental"
    assert "twice" in recommendation.explanation
