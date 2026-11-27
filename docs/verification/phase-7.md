# Phase 7 · Reproducible offline release

**Offline release gate PASS locally. Live smoke and full live pair BLOCKED / UNVERIFIED.** No real provider requests or charges occurred. Headless Chromium exercised the local UI. The release workflow repeats the full gate, audits and secret scans on Windows and Ubuntu.

## Initial clean setup

Tested on Windows 11 x64 build 26300, Intel Core Ultra 5 225H, 14 logical processors visible, CPython 3.12.15, uv 0.13.1, Node 24.22.3 and npm 11.19.1. The clean checkout started from Phase 6 and received the staged release patch. Its Git tree matched the staged source byte for byte at `d99835edf32a6e3ebd996391ef6a109436b2de1c` before this report was added. It had its own virtual environment, npm installation and built frontend.

| Executed command | Exit | Observed result |
| --- | ---: | --- |
| `uv --offline --directory backend sync --locked` | 0 | Installed the editable project and locked Python dependencies from the local cache. |
| `npm --offline --prefix frontend ci --no-audit` | 0 | Installed 32 packages on Windows. Both lockfile digests matched the source checkout after setup. |
| `uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 7` | 0 | 157 backend tests passed in 12.42 s, including 150 passing generated kernel sequences. Two frontend unit tests, TypeScript, build, lint, real Chromium E2E, offline demo, published export verification, coverage and benchmark all passed. |
| `python scripts/release_audit.py --gitleaks <verified-binary>` in the clean environment | 0 | OSV found zero known vulnerabilities or adverse statuses in 28 Python packages. npm reported zero vulnerabilities. Gitleaks 8.30.1 scanned all seven preceding commits, the staged candidate and the built client with zero findings. |
| `gitleaks dir --redact --no-banner .local/phase7-evidence` | 0 | The generated JSON and CSV evidence produced zero secret findings. |
| `actionlint .github/workflows/ci.yml` | 0 | Both hosted runner definitions and release audit steps passed static validation. |

The verifier clears provider credentials and disables live mode. The offline network test blocks socket connections during creation, both branches and export. Chromium observed zero external requests and zero normal-path console errors at 1280 × 720, 1440 × 900 and 390 × 844. An explicit API outage rendered an error. The API rejects a non-loopback peer presenting a loopback host. Redaction tests checked the persisted attempt receipts, exports and captured output with a server-only marker.

## Coverage and benchmark

Critical modules executed **738 of 762 statements (96.85%)**. The gate enforces at least 85% on each module individually. The lowest was the social reducer at 87.76%. The economic reducer reached 95.45% and authorized observation reached 97.06%. The first release run exposed a Windows pathname type mismatch in the coverage reporter. Passing filenames in the coverage library's supported format fixed the report. Invariant tests directly exercised invalid debit/credit entries, incorrect boundaries and conservation failures.

Seven fresh SQLite experiments measured parent setup, independent forks, turn-by-turn persistence, settlement and verified comparison. Timing excluded Python startup, dependency installation, schema initialization and UI startup.

| Pair | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Seconds | 0.694 | 0.727 | 0.697 | 0.737 | 0.690 | 0.687 | 0.689 |

**Median 0.694 s**, target under 5 s. Every sample contained six agents, eight rounds and 48 turns per branch.

## Replay and experiment evidence

The standalone checker reconstructed 66 events and 11 checkpoints in A, and 67 events and 12 checkpoints in B. It verified both integrity chains, the shared prefix and assigned grant, every settled metric and all paired differences. Mutation tests rejected altered events, checkpoints, metrics and a fabricated delta on an incomplete pair. Branch isolation tests covered balances, commitments, notes, grants and history. [Complete recorded export](phase-7-pair.json) · [Branch-isolation gate](phase-4.md) · [Dashboard and replay evidence](phase-6.md)

| Digest | SHA-256 |
| --- | --- |
| Shared pre-intervention state | `74dcef0e80412b8a9de41308953bc9ca3a303dc22e6087865a02dfbbf0e51197` |
| A final state | `bd6be568c248087b3949dbd818ae04ca224cc24be6436b7d7748cb952e950c98` |
| B final state | `1553892ab5fb8e512e1ee12566260aad085859bdd4e432546c13ca8fc7094cae` |

Seed 42, one completed rule-based pair. Both branches consumed 20 units and ended with 22 food and 28 unmet units. The primary difference, B minus A, was zero. Full evidence access changes the domain state even when selected outcome metrics coincide.

## Limits and remaining work

The real-provider smoke, authorized paired live experiment, pricing and empirical evaluation remain outstanding. The zero-network budget preview for a 96-call, one-million-token allowance estimated 929,406 reserved tokens over 96 offline reference contexts. The largest primary reservation was 10,479 tokens. Actual live contexts and retries can differ. Mock tests proved a reservation existed before transport, an interrupted call preserved the pending world turn, another branch could not spend an unresolved allowance, and a provider echo of the credential could not enter exported notes. Real billing and latency remain unknown.

The application supports one trusted operator on loopback. Database tamper resistance against its owner, multi-user hosting, distribution licensing and optional Phase 8 extensions are outside this verified release.

## Hosted Windows benchmark correction

The first release candidate passed the Ubuntu job and completed all functional checks on the hosted Windows runner. Windows measured a median of **5.443 s** and correctly failed the 5 s benchmark. A fresh Windows clone of the identical GitHub commit passed locally with a 0.730 s median. [Original release run](https://github.com/guptavernit2-afk/Agentverse-lab/actions/runs/45976520025)

The experiment opened and closed a SQLite connection for every event and repeatedly created a rollback journal. The correction uses write-ahead logging and keeps an idle connection open for each branch. Each event still commits in its own transaction with SQLite synchronous mode FULL. No transaction spans a provider call. A new regression test observed committed progress from another connection, interrupted a subsequent transaction, verified rollback and recovered the exact retried state after reopening.

The complete corrected local gate passed with **158 backend tests**, 150 generated sequences, two frontend unit tests, Chromium E2E, 96.85% critical-module coverage and independent verification of the earlier published export. The seven measured pairs took 0.243, 0.198, 0.209, 0.198, 0.191, 0.193 and 0.200 s. **Median 0.198 s** on the same developer hardware. The threshold, workload, sample count and durability assertions remain enforced.
