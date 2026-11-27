# Scenarios

Scenario files use versioned JSON. The Phase 0 header is defined by [`ScenarioHeader`](../backend/src/agentverse/experiments/scenario_schema.py).

```json
{
  "scenario_id": "food-scarcity",
  "schema_version": 1
}
```

The example describes the header shape. The executable [town baseline](town-v1.json) supplies the grid, six profiles, workplaces, zone capacities, treasury, and harvest for each round. Coordinates are zero-based `[x, y]`. Each `.` in a grid row is walkable and each `#` is blocked. The baseline supplies six food per round for eight rounds. The controlled scarcity experiment belongs to Phase 5.
