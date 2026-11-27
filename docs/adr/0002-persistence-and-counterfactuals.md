# Durable turns, replay and paired experiments

**Status · Accepted for the local MVP**

The kernel accepts an actor's strict proposal against the issued turn version. Production, consumption and authoritative grants enter through trusted scenario operations. Both offline and live policies receive the same allowlisted historical observation. Operator projections include private facts and carry a separate view label.

SQLite persists run metadata, events, command receipts, checkpoints, experiment assignments, branch statuses, provider-attempt receipts and operator controls. Each event references a command and sequence. Its integrity chain starts at the canonical genesis hash. A versioned snapshot contains the canonical domain representation. Loading reconstructs the complete prefix through the reducer and checks the chain, every required checkpoint and the run head. Exports carry the data needed to repeat these checks without a database or policy.

The store uses SQLite write-ahead logging with synchronous mode FULL. Experiment execution reuses its connection while committing each event independently. A write transaction checks the expected head before appending effects. Command receipts bind an idempotency key to its input and original result. Round controls also carry a revision to distinguish pause and start at the same event version. Scheduled work commits at a round boundary. Experiment turns commit individually. A soft interruption retains committed work. A process restart allows an offline branch to continue from its verified cursor.

The scarcity protocol forks two independent copies of a verified round-zero prefix. The branch assignment changes access to one existing record. Metrics use committed events and settled worlds. Incomplete pairs retain their histories and yield an unavailable paired delta. Elapsed times, IDs, budgets and provider diagnostics stay outside the normalized domain hash.

A live attempt reserves budget before sending. The durable receipt contains its logical cursor, actor, reservation, status, optional usage and output hash. Network I/O occurs outside SQLite transactions. Uncertain attempts keep their reservation and block additional live billing on that pair after interruption. The stored manifest retains the configured provider, model, policy and prompt versions. A configured price produces an estimate.

This architecture serves one trusted loopback operator and one Uvicorn worker. Full replay and independent prefix copies fit the bounded six-agent scenario. The SHA-256 checks support reproducibility and corruption detection. Authenticity against a malicious database owner would require a separate trust mechanism.
