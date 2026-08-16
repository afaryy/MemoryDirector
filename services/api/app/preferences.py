from collections import Counter
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PreferenceRecommendation:
    music_direction: str
    evidence_count: int
    explanation: str


class McpToolCaller(Protocol):
    def call_tool(self, name: str, arguments: dict[str, str]) -> str: ...


class FakePreferenceRepository:
    def __init__(self, history: list[str]) -> None:
        self._history = history

    def recommend(self, user_id: str, occasion: str) -> PreferenceRecommendation:
        accepted = [choice for choice in self._history if not choice.endswith(" rejected")]
        top_choice, evidence_count = Counter(accepted).most_common(1)[0]
        return PreferenceRecommendation(
            music_direction=f"{top_choice} instrumental",
            evidence_count=evidence_count,
            explanation=f"You chose {top_choice} {number_word(evidence_count)} before for similar memories.",
        )


class ClickHouseMcpPreferenceRepository:
    def __init__(self, caller: McpToolCaller) -> None:
        self._caller = caller

    def recommendation_query(self, user_id: str, occasion: str) -> str:
        safe_user_id = user_id.replace("'", "''")
        safe_occasion = occasion.replace("'", "''")
        return f"""
SELECT value, count() AS evidence_count
FROM creative_preferences
WHERE user_id = '{safe_user_id}'
  AND occasion = '{safe_occasion}'
  AND decision = 'accepted'
GROUP BY value
ORDER BY evidence_count DESC, value ASC
LIMIT 1
""".strip()

    def load_raw_recommendation(self, user_id: str, occasion: str) -> str:
        return self._caller.call_tool(
            "run_query",
            {"query": self.recommendation_query(user_id, occasion)},
        )


def number_word(value: int) -> str:
    return {1: "once", 2: "twice"}.get(value, f"{value} times")
