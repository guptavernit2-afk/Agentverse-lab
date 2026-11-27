import json
from pathlib import Path

import pytest

from agentverse.experiments.town import TownScenario

SCENARIO = Path(__file__).resolve().parents[2] / "scenarios" / "town-v1.json"


@pytest.fixture(scope="session")
def town():
    return TownScenario.model_validate_json(SCENARIO.read_bytes())


@pytest.fixture
def scenario_data():
    return json.loads(SCENARIO.read_bytes())
