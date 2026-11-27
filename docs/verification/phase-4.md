# Phase 4 · Persistence, replay and branching

**Local cumulative gate PASS.** Windows x64, CPython 3.12.15, Node 24.22.3, standard-library SQLite. No dependency changes.

| Command | Exit | Observed result |
| --- | ---: | --- |
| `uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 4` | 0 | 131 tests passed in 2.38 s, 150 generated sequences passed. Backend import, frontend typecheck and build passed. |
| `node .local/verify-phase0-runtime.mjs` | 0 | HTTP 200, both shell sizes rendered, zero console errors and zero external page requests. |
| `actionlint .github/workflows/ci.yml` | 0 | Workflow passed static validation. |

The replay test compared every historical world digest with the executed kernel and compared each snapshot against its reconstructed world. A policy that would fail on invocation guarded replay. Restart at a committed promise preserved the turn, balances, private note and ledger. SQLite aborted an injected failure between event insertion and snapshot insertion and recovered the previous head. Ten storage damage cases blocked both load and fork. Concurrent duplicate submissions resulted in one food transfer. Independent child A acquired a grant, private note and promise. Parent and child B retained their original histories and observations.

Each SQLite connection enables foreign keys. Numbered migrations, command receipts, hashed event chain, checkpoints, and run head use explicit transactions. Forked histories contain independent copies of the verified prefix. Integrity checks detect accidental corruption and assume a trusted local database owner. Full replay and copied prefixes favor clarity for the bounded MVP.

A process lost after a provider response and before commit leaves the last durable turn pending. A later explicit retry can incur another provider charge. A lost response to a committed command can be recovered by its receipt. A fresh process must obtain a new approved live allowance before making further live calls. Live integration remains unverified.
