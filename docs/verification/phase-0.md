# Phase 0 · Repository setup and architectural contract

Gate verdict · **PASS**

Verification date · 27 November 2026

Environment · Windows x64, PowerShell 7.6.9, CPython 3.12.15, uv 0.13.1, Node.js 24.22.3, npm 11.19.1

## Changes

| Area | Files and behavior |
|---|---|
| Repository | `PRD.md` preserves the supplied attachment. `AGENTS.md` records phase approval. `README.md`, `.gitignore`, `.gitattributes`, and `.env.example` cover setup and local defaults. |
| Backend | `backend/` contains the locked Python package, loopback health route, strict scenario header, and smoke tests. |
| Frontend | `frontend/` contains the locked React and TypeScript scaffold with a Vite production build and local preview. |
| Verification | `scripts/verify.py` and `.github/workflows/ci.yml` share the mandatory checks. The workflow defines Windows and Linux runners and requires no provider credentials. |
| Architecture | `docs/adr/0001-state-authority.md`, `docs/decisions.md`, `docs/progress.md`, and `scenarios/README.md` record the design boundaries, dependency and license choices, and scenario header. |

## Executed checks

| Command | Exit | Actual result |
|---|---:|---|
| `git ls-remote --symref` against the linked repository | 0 | Empty ref listing. The subsequent clone confirmed an empty repository. |
| `uv --directory backend sync --locked` | 0 | Fresh Python 3.12.15 environment with 24 packages installed. SHA-256 of `uv.lock` was identical before and after the locked sync. |
| `npm.cmd --prefix frontend ci` | 0 | 27 packages installed with no prior `node_modules`. SHA-256 of `package-lock.json` was identical before and after installation. |
| `uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 0` | 0 | Backend import, pytest, frontend type check, and frontend build each exited 0. The final run reported 8 passed in 0.44 s with no warnings. Vite built 16 modules. |
| `node .local/verify-phase0-runtime.mjs` | 0 | Uvicorn health check and Chromium production preview succeeded. The one-off verification harness used the pinned runtimes and local services. |
| `actionlint -color=false .github/workflows/ci.yml` | 0 | Workflow validation succeeded with actionlint 1.7.12. |
| `git ls-files --error-unmatch backend/uv.lock frontend/package-lock.json` | 0 | Both lockfiles were in the reviewed 33-file Git index. |
| `git diff --cached --check -- . ':(exclude)PRD.md'` | 0 | Authored files passed the whitespace check. The source PRD was checked byte for byte to preserve its Markdown formatting. |
| Targeted credential check with `git grep --cached` | 1 | No matches for common provider tokens, private key headers, or credentials embedded in URLs. Exit 1 means no matches. |

The first verifier run reported 8 passes and one Starlette deprecation warning for HTTPX. The backend development pin was changed to HTTPX2, the lockfile was regenerated, and the final locked sync was repeated in a fresh environment. The final verifier used offline uv and npm commands with provider environment variables cleared.

## Checks of the Phase 0 contracts

- The ASGI smoke test verified HTTP 200 and the installed service version. The scenario tests accepted a version 1 header and rejected unsupported, mistyped, and missing versions, a blank scenario ID, and an unknown field.
- The PRD attachment and repository copy had matching SHA-256 hashes, and Git staged the same bytes. The Phase 0 verifier executed zero provider calls.
- The scenario schema and architectural boundaries are scaffolds. Verification of world state, evidence access, branching, and replay belongs to the phases that implement them.

## Manual API and browser verification

- The running Uvicorn service returned HTTP 200 at `http://127.0.0.1:8000/health` with `{"status":"ok","version":"0.1.0"}`.
- Chromium 159.0.8154.6 loaded the built Vite shell at `http://127.0.0.1:4173` at 1280 × 720 and 390 × 844. The title and inactive run status were visible at both sizes, with zero console errors or external page requests and no horizontal overflow.
- The desktop capture was visually inspected. [Phase 0 shell screenshot](phase-0-shell.png)

## Limitations and approval

The authored workflow was validated locally. Hosted Windows and Linux job outcomes are unverified and require an actual GitHub Actions run. The Phase 0 gate covers the local scaffold and workflow checks defined in the approved plan.

Phase 1 requires separate owner approval.
