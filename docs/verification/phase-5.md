# Phase 5 · Controlled scarcity experiment

**Local cumulative gate PASS. Live UNVERIFIED.** Tested on Windows x64, Python 3.12.15 and Node 24.22.3 with provider keys cleared.

| Command | Exit | Actual result |
| --- | ---: | --- |
| `uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 5` | 0 | 135 tests passed in 2.61 s, 150 generated sequences passed, backend import, typecheck, build and paired CLI demo passed. |
| `python scripts/demo.py --scenario food-scarcity --mode rule_based --seed 42 --output .local/phase5-evidence` (backend interpreter) | 0 | Wrote SQLite, complete JSON manifest/history/metrics and long-form CSV. One completed pair. |
| `node .local/verify-phase0-runtime.mjs` and workflow actionlint | 0 each | Health returned 200. Two sizes rendered, zero console errors and zero external requests. |

The initial run found a strict schema mismatch between JSON arrays and typed scenario tuples. The scenario transformation now preserves native tuples and runs full validation. The corrected gate passed.

| Seed 42 cumulative metric | A · private record | B · public record |
| --- | ---: | ---: |
| Scheduled decisions | 48 | 48 |
| Starting food | 18 | 18 |
| Food produced | 24 | 24 |
| Food consumed | 20 | 20 |
| Unmet demand | 28 | 28 |
| Remaining food | 22 | 22 |
| Gift units | 13 | 13 |
| Rejected proposals | 2 | 2 |
| Mean directed trust | 50 | 50 |
| Provider calls | 0 | 0 |

Both children shared pre-intervention state hash `74dcef0e80412b8a9de41308953bc9ca3a303dc22e6087865a02dfbbf0e51197`. Only B received the grant. For each agent the earlier observation still hid the record. A second independently created pair reproduced both histories and all domain metrics. The tests checked hand-calculated trust, fulfillment, inequality, invalid proposals, transfers, zero denominators and signed B minus A deltas. A mock live pair halted before any request and produced no completed-pair delta.

Each row is cumulative through settlement of the displayed round. Trade units exclude gifts and promise fulfillment. Invalid rate uses proposals that reached validation and excludes provider failures. Runtime telemetry records elapsed policy execution separately from logical time. Missing rates export as JSON null and empty CSV cells. Wall times and generated run IDs vary. This one rule-based pair produced a zero primary difference and supplies functional evidence only.
