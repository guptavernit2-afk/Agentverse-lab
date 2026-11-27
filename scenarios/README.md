# Scenarios

Scenario files use versioned JSON. The Phase 0 header is defined by [`ScenarioHeader`](../backend/src/agentverse/experiments/scenario_schema.py).

```json
{
  "scenario_id": "food-scarcity",
  "schema_version": 1
}
```

The example describes the header shape. The simulation kernel and experiment phases add the world configuration and protocol.
