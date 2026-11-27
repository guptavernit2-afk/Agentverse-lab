# AgentVerse Lab

Use [PRD.md](PRD.md) as the product and verification specification.

- Work on one owner-approved phase at a time. Before editing, agree on scope, files, dependencies, risks, and checks.
- Keep the simulation engine authoritative. Policies propose actions from authorized observations. API and UI consume projections. Keep I/O outside the deterministic reducer.
- Run the current phase gate and all earlier regression checks. Record commands, actual exit codes and counts, manual observations, limitations, and the gate verdict in `docs/verification/phase-N.md`.
- Record architecture in `docs/adr/`, decisions and deviations in `docs/decisions.md`, and open work in `docs/progress.md`.
- Continue to the next phase only after a passing mandatory gate and separate owner approval.
- Keep provider calls out of the default workflow. Live calls, paid infrastructure, publishing, pushes, and deployment require explicit owner approval. Keep credentials out of repository files, logs, tests, and client builds.
