# Phase 1 · Deterministic simulation kernel and economy

**Gate verdict · PASS locally**

Verified on Windows x64 with CPython 3.12.15, uv 0.13.1, Node 24.22.3, npm 11.19.1, pytest 9.2.0, and Hypothesis 6.170.17.

## Scope and files

- `scenarios/town-v1.json` and `backend/src/agentverse/experiments/town.py` define and validate the map, six profiles, resources, workplaces, and harvest schedule.
- `backend/src/agentverse/domain/` defines immutable world state, structured proposals, atomic events, ledger application, invariants, and normalized state hashes. `backend/src/agentverse/simulation/` validates proposals and serializes turn and round transitions.
- `backend/src/agentverse/cli.py` runs labeled developer fixtures through the public kernel. `backend/tests/test_kernel*.py` and `conftest.py` contain gate tests. The verifier, CI workflow, project manifests, lockfile, README, and decision log were updated for the new phase.

## Executed checks

| Command | Exit | Observation |
|---|---:|---|
| `uv --offline --directory backend sync --locked` in a fresh copy of the staged tree | 0 | Created a new Python environment and installed 26 packages from the local cache. uv fell back from hardlinking to copying. |
| `npm.cmd --offline --prefix frontend ci --no-audit` in that copy | 0 | Installed 27 packages with a fresh node_modules directory. Both lockfile hashes matched their pre-install hashes. |
| `uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 1` in that copy | 0 | Backend import, pytest, TypeScript check, and Vite production build each exited 0. **58 passed in 2.64 seconds** with provider keys cleared. |
| Hypothesis statistics from the gate | 0 | 150 passing sequences, zero failures, six discarded generation attempts. Each completed sequence included accepted and rejected turns. |
| `node .local/verify-phase0-runtime.mjs` | 0 | The running health endpoint returned HTTP 200 and service version 0.1.0. Chromium rendered the inactive shell at 1280 × 720 and 390 × 844 with zero console errors and zero external page requests. |
| `actionlint .github/workflows/ci.yml` | 0 | The Windows and Linux workflow definition passed static validation. |

## Kernel invariants and determinism

- Tests checked exact initialization, seed-dependent round rotation, six sequential turns per round, settlement and run limits. Ledger checks reconciled both sides of transfers and actual harvest and consumption. Tests checked nonnegative balances, walkability, zone capacity, workplace eligibility, treasury depletion, offer expiry and revocation, and settlement on the expiry round.
- For a rejected current-turn proposal, tests checked the recorded WAIT and reason, one cursor advance, and preservation of economic state. Stale and wrong-run tokens left the state untouched. Two competing submissions for one offer produced one exchange and one conflict. A later repeat acceptance also failed.
- Two fresh Python processes executed the economy fixture with simulation seed 42, distinct run IDs, and Python hash seeds 17 and 881. Initial hashes and all eight round records matched, including order, outcomes, ledger entries, and state hashes. A separate test changed one action at the same state version and observed a different domain hash.

## Manual CLI evidence

Executed `uv --offline --directory backend run --no-sync python -m agentverse.cli --scenario ../scenarios/town-v1.json --seed 42 --fixture economy` and repeated with `--fixture wait`. Both commands exited 0 and labeled their output `test_fixture`.

| Eight-round baseline | Economy fixture | All-WAIT fixture |
|---|---:|---:|
| Scheduled turns | 48 | 48 |
| Accepted / rejected | 37 / 11 | 48 / 0 |
| Food at opening / produced / consumed / closing | 18 / 48 / 20 / 46 | 18 / 48 / 19 / 47 |
| Cumulative unmet units | 28 | 29 |
| Closing agent coins / treasury | 210 / 0 | 150 / 60 |

The all-WAIT result at round two matched the independent calculation of 22 remaining food and four unmet units. The economy fixture exercised all seven action kinds. It ended with hash `df09cf4bffc971bdc62b8fcced4177249104c05edd1f8b71ec5e2b91ba683465`. The all-WAIT final hash was `29abf0a3b46cf7903dc34d7ab71b8a4727a35c6122dd931c0432bbd0ddce5450`.

## Limits and checkpoint

The gate covers a single-process in-memory kernel and scripted developer fixtures. Durable recovery, branching, and policy-driven experiments have later gates. Hosted CI status is available separately once the commit is published. Phase 2 requires owner approval.
