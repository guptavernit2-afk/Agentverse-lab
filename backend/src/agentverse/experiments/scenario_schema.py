from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ScenarioHeader(BaseModel):
    """Versioned metadata for the scenario configuration scaffold."""

    model_config = ConfigDict(strict=True, extra="forbid")

    scenario_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    schema_version: Annotated[int, Field(ge=1, le=1)]
