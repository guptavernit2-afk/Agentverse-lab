# Phase 2 · Social protocol, evidence and bounded observation

**Local gate verdict · PASS**

Windows x64 with CPython 3.12.15, uv 0.13.1, Node 24.22.3, npm 11.19.1, pytest 9.2.0 and Hypothesis 6.170.17. Phase 2 uses the existing locked dependencies.

## Scope

The kernel implements scoped speech, a public claim and authenticated harvest record, private and public grants, a commitment ledger, directed trust, private self-reports, and historical agent observations. Changes span the domain records and reducer, kernel and social action resolver, agent context serializer, CLI fixture, tests, verifier, CI, and documentation.

## Executed checks

| Command | Exit | Actual result |
|---|---:|---|
| `uv --offline --directory backend sync --locked` and `npm.cmd --offline --prefix frontend ci --no-audit` in a fresh staged-tree copy | 0 each | Installed 26 backend and 27 frontend packages. Both lockfile digests matched before and after setup. |
| `uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 2` | 0 | **96 tests passed in 2.28 s**. Backend import, TypeScript check, and production build each passed. Provider keys were cleared. |
| Hypothesis economy checks in the same gate | 0 | 150 passing sequences, zero failing sequences, five discarded generation attempts. |
| `node .local/verify-phase0-runtime.mjs` | 0 | The running health endpoint returned HTTP 200 and version 0.1.0. Chromium rendered the shell at 1280 × 720 and 390 × 844 with zero console errors and zero external page requests. |
| `actionlint .github/workflows/ci.yml` | 0 | The two-runner workflow passed local static validation. |

The first clean-tree run reported 95 passes and one test setup failure. Refactoring a shared helper had left a stale reference to a WAIT constant. The corrected test supplies the actual WAIT proposal and still asserts a stale-turn conflict. The full verifier was rerun in the clean environment.

## Privacy and invariant evidence

- Two independent worlds differed in private messages, notes, inventory, seed memory, harvest payload, and grants. An unrelated agent's serialized policy context, including its retrieved memory, matched byte for byte and matched an explicitly constructed allowlist snapshot.
- A direct recipient saw the message while its private attachment was filtered. A public grant revealed the authorized payload. An earlier version still reproduced its pre-grant bytes. Tests also covered private-record existence, visible offer IDs, memory truncation, and personally unresolved obligations.
- Forged issuance, forged status, unavailable references, and remote private communication were rejected. A public statement claiming delivery preserved inventory, commitment, trust, and world facts. A private belief or summary remained attributable to its author.
- Fulfillment tests covered full, partial, due-round, excessive, remote, unfunded, and late delivery. Concurrent retries produced one successful transfer. The reducer rejected a fulfillment without its matching ledger transfer. Breach retained partial progress. Tests checked all 30 directed trust edges and both clamp limits.

## Manual trace

Ran `uv --offline --directory backend run --no-sync python -m agentverse.cli --scenario ../scenarios/town-v1.json --seed 42 --fixture social` (exit 0). The trace identified its mode as `test_fixture` and its view as `operator`.

| Promise | Committed events | Observed outcome |
|---|---|---|
| A1 promised A2 two food due in round 3 | 5 → 18 → 25 | Events 18 and 25 each transferred one food from A1 to A2. The second delivery fulfilled the promise on its due round. A2's trust in A1 changed from 50 to 58. |
| A2 promised A1 one food due in round 2 | 13 → 19 | Settlement recorded a breach with zero delivered. A1's trust in A2 changed from 50 to 38. |

The other 28 trust edges stayed at 50. The eight-round fixture ended with 46 food (18 initial + 48 produced − 20 consumed), 28 unmet units, and 210 coins including the treasury. Final domain hash: `2458a4b15928f78dec56cc90a07e72606cbe89720ec505522a6b92d012b4cff9`.

## Limitations

The historical observations and event log are held in memory. The serializer provides the agent context for the upcoming policy interface. Provider calls and durable restart recovery have their own Phase 3 and Phase 4 gates. The manual trace demonstrates scripted mechanics. Phase 3 requires owner approval.
