# Decisions and deviations

## Phase 0 toolchain

| Area | Choice | Direct dependency licenses |
|---|---|---|
| Backend | CPython 3.12.15 and uv 0.13.1. FastAPI serves the HTTP boundary, Pydantic defines typed schemas, and Uvicorn runs the local service. pytest and HTTPX2 exercise the app in-process. | FastAPI, Pydantic, and pytest use MIT. Uvicorn and HTTPX2 use BSD-3-Clause. uv and uv-build are dual-licensed MIT or Apache-2.0. |
| Frontend | Node.js 24.22.3 and its bundled npm 11.19.1. React and React DOM render the shell, Vite builds it, and TypeScript checks it. | React, React DOM, Vite, the React plugin, and the type declaration packages use MIT. TypeScript uses Apache-2.0. |

Exact direct versions are in the project manifests. `uv.lock` and `package-lock.json` pin installed dependencies. Node 24.22.3 is a patched release in the approved Node 24 line. [Node.js release](https://nodejs.org/en/blog/release/v24.22.3)

The scenario header model is the source for its validation and JSON Schema. Scenario data and the full scenario contract will be added in their implementation phases.

The project distribution license remains an owner decision. Track third-party notice obligations before public release.

## Deviations

The first smoke run exposed Starlette's deprecation of HTTPX as a test transport. The final development pin uses HTTPX2, which supports the existing test through FastAPI's `TestClient`. [Starlette TestClient documentation](https://starlette.dev/testclient/)

Verification details and limitations are in the [Phase 0 report](verification/phase-0.md).

## Phase 1 kernel rules

- Agent IDs sort lexically. In logical round `r` (starting at 1), the first turn is at index `(seed + r - 1) % 6`. Round start credits the configured harvest to the farmer. Settlement takes one food from each agent who has it and records the remaining agents as hungry. The last entry in the harvest schedule ends the run.
- Movement uses one cardinal step. Agents can share tiles within the configured zone capacity. A gift or accepted trade requires the same tile. A wage of two coins requires the agent's configured workplace, presence in its zone, and a funded treasury.
- An offer sells a positive quantity of the seller's food for a positive total coin price. Each input is capped at 1,000,000. Posting requires sufficient food and leaves it available. Acceptance rechecks both parties' resources. The expiry round can range from the current round through the final configured round, inclusive. Settlement expires open offers due that round.
- The kernel serializes access to a run. A caller presents the issued turn and expected version. Each accepted turn or recorded rejection advances that turn once. A mismatched token raises a conflict before any state change. Command retries and crash recovery across process lifetimes belong to Phase 4.
- The reducer builds an immutable candidate world for each event and checks invariants before the kernel commits it. Each ledger entry names the asset, positive amount, source, and destination. A null account denotes external harvest or consumed food. The treasury uses the reserved ID `@treasury`.
- Domain hashes use SHA-256 of UTF-8 canonical JSON covering the configuration, seed, logical cursor, holdings, unmet demand, last action status, offers, and economic counters. The run identifier belongs to the trusted turn envelope. Events use increasing sequence numbers and offers use their creation event's sequence.
- Hypothesis 6.170.17 is a locked development dependency. The generated test prints the world seed and action inputs on failure through Hypothesis's falsifying example and enables its reproduction blob.
