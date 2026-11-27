import pytest
from pydantic import ValidationError

from agentverse.experiments.scenario_schema import ScenarioHeader


def test_valid_scenario_header() -> None:
    header = ScenarioHeader.model_validate_json(
        '{"scenario_id": "food-scarcity", "schema_version": 1}'
    )

    assert header.scenario_id == "food-scarcity"
    assert header.schema_version == 1


@pytest.mark.parametrize(
    "payload",
    [
        '{"scenario_id": "food-scarcity", "schema_version": 2}',
        '{"scenario_id": "food-scarcity", "schema_version": "1"}',
        '{"scenario_id": "food-scarcity", "schema_version": true}',
        '{"scenario_id": "food-scarcity"}',
        '{"scenario_id": "  ", "schema_version": 1}',
        '{"scenario_id": "food-scarcity", "schema_version": 1, "extra": 1}',
    ],
    ids=[
        "unsupported-version",
        "string-version",
        "boolean-version",
        "missing-version",
        "blank-scenario-id",
        "unknown-field",
    ],
)
def test_invalid_scenario_header(payload: str) -> None:
    with pytest.raises(ValidationError):
        ScenarioHeader.model_validate_json(payload)
