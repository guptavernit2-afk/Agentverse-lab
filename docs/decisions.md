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
