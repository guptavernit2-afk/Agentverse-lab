# Phase 6 · Local API and interactive dashboard

**Local cumulative gate PASS. Live UNVERIFIED.** Windows x64, CPython 3.12.15, Node 24.22.3, Playwright 1.65.1 and Chromium. The server and all browser assets ran locally with provider keys cleared.

| Executed check | Exit | Observed result |
| --- | ---: | --- |
| `uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 6` | 0 | 140 backend tests, 150 generated sequences and 2 frontend unit tests passed. Backend import, TypeScript, production build, paired CLI, lint and Chromium E2E all passed. |
| `npm --offline --prefix frontend run test:e2e` with screenshot directory | 0 | Real backend, isolated SQLite file, no external page requests and zero normal-path console errors. |
| `actionlint .github/workflows/ci.yml` | 0 | Both runner definitions validated. |

The API tests covered strict request fields and size limits, local origin enforcement, duplicate requests, stale domain and control versions, start/pause/step/stop, terminal states, protocol-controlled child runs, ordered event pagination, websocket reconnect and gap recovery. The browser loaded operator and authorized agent projections, forked event 2 after stepping the parent, ran B then A, compared displayed values with the server, downloaded and parsed JSON and CSV, then scrubbed from before to after the treatment. At event 2 the B inspector saw the unverified claim. At event 3 it saw the grant. An unavailable health endpoint produced an error and disabled creation.

Inspected screenshots at 1280 × 720, 1440 × 900 and 390 × 844. Shifted controls above the map and separated co-located agent markers after the first inspection. Navigation, controls and roster remain reachable on the narrow layout. Accessibility lint initially rejected a generic control group. A native fieldset passed the repeated gate. Keyboard checks exercised run creation and the replay slider. [Town screenshot](phase-6-town.png) · [Paired comparison](phase-6-comparison.png)

The API serves a single trusted local operator. Agent views are experimental visibility boundaries. Anyone with local operator access can request omniscient data. Browser font files and map graphics are local. The live UI requires explicit server enablement, a configured model, a server credential and confirmed limits. The live UI and service have received no paid smoke test.
