# AgentVerse Lab

AgentVerse is a local simulation lab for studying how access to verifiable evidence affects decisions and cooperation in a six-agent town. The vision, phase roadmap, and acceptance gates are in [PRD.md](PRD.md). The [state authority ADR](docs/adr/0001-state-authority.md) records the boundaries that govern later implementation.

Phase 1 provides an in-memory deterministic town economy and an offline CLI. The API and frontend retain their Phase 0 health endpoint and inactive shell. See the [Phase 1 verification report](docs/verification/phase-1.md).

## Setup and verification

Install [uv 0.13.1](https://github.com/astral-sh/uv/releases/tag/0.13.1) and [Node.js 24.22.3](https://nodejs.org/en/blog/release/v24.22.3), which includes npm 11.19.1. uv uses the Python 3.12.15 pin in `backend/.python-version` and can provision it on the first sync. Setup can download the pinned runtimes and packages. Verification and preview run with local dependencies and require no provider account or credentials.

Run the commands from the repository root.

### Windows PowerShell

```powershell
uv --directory backend sync --locked
npm.cmd --prefix frontend ci
uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 1
```

### Unix

```sh
uv --directory backend sync --locked
npm --prefix frontend ci
uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 1
```

The verifier runs the application import check, pytest, the frontend type check, and the production build. It exits nonzero if any check fails.

## Kernel demo

Run the scripted economy fixture from the repository root.

```sh
uv --offline --directory backend run --no-sync python -m agentverse.cli --scenario ../scenarios/town-v1.json --seed 42
```

The JSON trace labels the mode as `test_fixture` and includes all turns, rejection reasons, ledger entries, unmet demand, and round-end hashes. Use `--fixture wait` for the all-WAIT accounting example. Both fixtures are for developer verification.

## Local preview

Start the API from the repository root.

```sh
uv --offline --directory backend run --no-sync python -m uvicorn agentverse.api.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/health`. The response should be HTTP 200 with `{"status":"ok","version":"0.1.0"}` for this scaffold. The keys in `.env.example` show the equivalent Uvicorn process defaults.

After a successful build, preview the frontend in a separate terminal. Use `npm` in place of `npm.cmd` on Unix.

```powershell
npm.cmd --offline --prefix frontend run preview
```

Open `http://127.0.0.1:4173` to see the AgentVerse Lab shell and its inactive run status.
