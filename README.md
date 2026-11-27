# AgentVerse Lab

AgentVerse is a local simulation lab for studying how access to verifiable evidence affects decisions and cooperation in a six-agent town. The vision, phase roadmap, and acceptance gates are in [PRD.md](PRD.md). The [state authority ADR](docs/adr/0001-state-authority.md) records the boundaries that govern later implementation.

The dashboard runs a deterministic town economy with scoped messages, evidence grants, food commitments and directed trust. SQLite stores replayable histories and independent branches. The paired scarcity experiment compares two evidence-access assignments. [Phase 5 experiment evidence](docs/verification/phase-5.md)

## Setup and verification

Install [uv 0.13.1](https://github.com/astral-sh/uv/releases/tag/0.13.1) and [Node.js 24.22.3](https://nodejs.org/en/blog/release/v24.22.3), which includes npm 11.19.1. uv uses the Python 3.12.15 pin in `backend/.python-version` and can provision it on the first sync. Setup can download the pinned runtimes and packages. Verification and preview run with local dependencies and require no provider account or credentials.

Run the commands from the repository root.

### Windows PowerShell

```powershell
uv --directory backend sync --locked
npm.cmd --prefix frontend ci
Push-Location frontend
npx.cmd --no-install playwright install chromium
Pop-Location
uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 6
```

### Unix

```sh
uv --directory backend sync --locked
npm --prefix frontend ci
(cd frontend && npx --no-install playwright install --with-deps chromium)
uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 6
```

The verifier runs backend tests, a paired offline demo, frontend lint, unit tests, typecheck, build and a Chromium workflow against an isolated local API. It exits nonzero if any check fails.

## Kernel demo

Run the scripted economy fixture from the repository root.

```sh
uv --offline --directory backend run --no-sync python -m agentverse.cli --scenario ../scenarios/town-v1.json --seed 42
```

The JSON trace is an operator view labeled `test_fixture`. It includes turns, rejection reasons, ledger entries, unmet demand, and round-end hashes. Use `--fixture wait` for the all-WAIT accounting example or `--fixture social` for a partial delivery, a fulfilled promise, and a breach. For an individual agent, `kernel.observe(agent_id, version=version).policy_context` returns canonical JSON with its permitted observation and bounded memory at that committed version.

## Local preview

Start the API from the repository root.

```sh
uv --offline --directory backend run --no-sync python -m uvicorn agentverse.api.main:app --host 127.0.0.1 --port 8000
```

Open the [local dashboard](http://127.0.0.1:8000). The API serves the built frontend on the same loopback origin. Choose **New run**, **Step round**, and select an agent. In **Experiment lab** fork event 2, run A and B, and compare or export the results. **Inspect history B** opens a verified replay. The agent inspector uses grants as of the selected event.

For frontend development, run `npm --prefix frontend run dev` alongside the API. The Vite server proxies HTTP and WebSocket requests to the local backend.

Run the offline paired CLI from the project root.

```sh
uv --offline --directory backend run --no-sync python ../scripts/demo.py --mode rule_based --seed 42 --scenario food-scarcity --output ../.local/demo
```

The output directory receives a SQLite database, a JSON file containing the manifest, ordered histories and metrics, and a long-form metrics CSV. Source runs and histories are trusted local operator data. Live provider testing requires separate operator authorization.
