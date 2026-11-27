"""Versioned configuration for the six-agent economy."""

from collections import Counter
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .scenario_schema import ScenarioHeader

Position = tuple[int, int]
Name = Annotated[str, Field(min_length=1, pattern=r"\S")]
Stock = Annotated[int, Field(ge=0)]


class ConfigRecord(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class Zone(ConfigRecord):
    id: Name
    tiles: Annotated[tuple[Position, ...], Field(min_length=1)]
    capacity: Annotated[int, Field(gt=0)]


class Profile(ConfigRecord):
    id: Name
    role: Name
    goal: Name
    seed_memory: Name
    profile_version: Annotated[int, Field(gt=0)]
    workplace: Name
    position: Position
    food: Stock
    coins: Stock


class TownScenario(ScenarioHeader):
    model_config = ConfigDict(frozen=True)

    grid: Annotated[tuple[str, ...], Field(min_length=1)]
    zones: tuple[Zone, ...]
    profiles: Annotated[tuple[Profile, ...], Field(min_length=6, max_length=6)]
    farmer_id: Name
    treasury: Stock
    harvest: Annotated[tuple[Stock, ...], Field(min_length=1)]

    def walkable(self, position: Position) -> bool:
        x, y = position
        return 0 <= y < len(self.grid) and 0 <= x < len(self.grid[y]) and self.grid[y][x] == "."

    @model_validator(mode="after")
    def validate_layout(self) -> "TownScenario":
        width = len(self.grid[0])
        if not width or any(len(row) != width or set(row) - set(".#") for row in self.grid):
            raise ValueError("grid must be rectangular and contain only floor and obstacle tiles")
        if len({profile.id for profile in self.profiles}) != len(self.profiles):
            raise ValueError("agent IDs must be unique")
        if self.farmer_id not in {p.id for p in self.profiles if p.role == "Farmer"}:
            raise ValueError("harvest recipient must be a configured farmer")
        zones = {zone.id: zone for zone in self.zones}
        if len(zones) != len(self.zones):
            raise ValueError("zone IDs must be unique")
        tiles = [tile for zone in self.zones for tile in zone.tiles]
        if len(set(tiles)) != len(tiles) or not all(map(self.walkable, tiles)):
            raise ValueError("zone tiles must be unique and walkable")
        occupancy = Counter(p.position for p in self.profiles)
        for profile in self.profiles:
            if not self.walkable(profile.position) or profile.workplace not in zones:
                raise ValueError("invalid start position or workplace")
        for zone in self.zones:
            if sum(occupancy[tile] for tile in zone.tiles) > zone.capacity:
                raise ValueError("initial zone occupancy exceeds capacity")

        start = self.profiles[0].position
        reachable = {start}
        pending = [start]
        while pending:
            x, y = pending.pop()
            for tile in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                if tile not in reachable and self.walkable(tile):
                    reachable.add(tile)
                    pending.append(tile)
        if (set(tiles) | set(occupancy)) - reachable:
            raise ValueError("agents and zones must share a connected walkable area")
        return self
