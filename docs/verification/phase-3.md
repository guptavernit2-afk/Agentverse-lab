# Phase 3 · Decision policies

**Offline gate PASS. Live Gemini integration BLOCKED / UNVERIFIED.**

Windows x64, Python 3.12.15 and Node 24.22.3. No new dependencies. Ran `uv --offline --directory backend run --no-sync python ../scripts/verify.py --phase 3` with provider keys cleared. Exit 0. All 113 tests passed in 1.85 s, including 150 generated kernel sequences. Backend import, TypeScript and Vite build passed. The existing Chromium runtime check `node .local/verify-phase0-runtime.mjs` passed on both viewports with zero console errors or external requests.

Two independent six-agent runs produced identical final state hashes across 48 decisions each. Tests exercised malformed and spoofed proposals, a private evidence guess, message instruction injection, failed authorization, retryable transport faults and interrupted calls. The mock inspected the actual prompt and checked the same serialized observation the kernel provided. Budget exhaustion preserved the pending turn. A retry charged a second reservation and committed one decision. Stored provider output diagnostics are SHA-256 hashes.

The rule policy fulfills nearby obligations, accepts affordable food offers when low on food, shares surplus with a nearby agent, then works at its workplace or waits. Its behavior has no treatment input. The live adapter uses a fixed operator-selected Gemini model, temperature zero, a versioned schema prompt and a conservative byte-based reservation. Unconfirmed attempts keep their reservation. Configured prices yield estimated bounds only. The model and budget for real experiments still require owner selection. No account or live service was used. [Gemini REST contract](https://ai.google.dev/api/generate-content)
