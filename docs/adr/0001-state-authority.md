# ADR 0001 · Simulation state authority

Status · Accepted for the Phase 0 architectural contract

## Decision

- The simulation engine owns world state. The trusted runtime supplies actor, run, turn, and expected state version. A policy receives an immutable authorized observation and returns a proposal. The engine validates the proposal and applies recorded world events atomically.
- The reducer is deterministic and independent of HTTP, storage, the frontend, provider I/O, wall time, and network access. The scheduler controls turn order from the seed and logical round. For an invalid proposal on the current turn, the runtime records the rejection and a `WAIT`. A stale response is rejected against its expected version so it cannot consume another turn.
- Allowlisted, version-specific projections serve agent observations and historical inspection. The separately labeled operator projection may include private state. Agent policies use the agent projection and their visible bounded history. The UI renders committed results from the API.
- Persistence records validated events and versioned snapshots. Replay applies those events without evaluating the policy. Normalized domain hashes support comparisons across branches. Event-stream integrity is checked separately.
- Branches start from a verified settled checkpoint and preserve independent writes. The paired experiment assigns evidence access as the treatment and keeps the initial world, shock, seed, schedule, and policy configuration fixed. Check the controlled diff before comparing outcomes.

## Consequences

Domain tests can exercise the engine independently of FastAPI, SQLite, React, and the model provider. Future gates check economy invariants before social rules, visibility before live decisions, and exact replay and fork isolation before experiment metrics. Phase 0 establishes the contract and the entry-point scaffolds.
