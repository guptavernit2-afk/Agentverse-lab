# AgentVerse — Autonomous Society & Counterfactual Simulation Lab

**Product Requirements Document (PRD) | v1.0 | 27 November 2026**  
**Status:** Proposed implementation specification; review before development.  
**Working name:** AgentVerse. Use a provisional repository name such as `agentverse-lab`; select a distinct public-facing name before release.  
**Audience:** Project owner, Codex, contributors and research evaluators.

---

## 0. Instructions to Codex — read before writing code

This is a specification for a multi-agent simulation, not a conventional CRUD application or a chatbot. Correctness of the world, information boundaries, and experiment integrity take priority over graphics and feature count.

1. Start in the new, user-selected repository. Inspect its contents and the development environment before changing anything. Do not modify other repositories or unrelated files.
2. Treat this PRD as the source of truth. Record architectural decisions in `docs/adr/`, deviations in `docs/decisions.md`, and unresolved issues in `docs/progress.md`. Propose alternatives when a requirement is infeasible; do not silently weaken it.
3. Implement one phase at a time. Before each phase, state the scope, expected files, dependencies, risks and test plan. Prefer small reviewable changes. Do not jump to future phases or perform a broad rewrite.
4. Use typed domain models, clear service boundaries, small functions and meaningful tests. Keep the simulation engine independent from the frontend, LLM provider and HTTP server. The engine is the only authority over world state.
5. Every phase ends with a gate: run all relevant tests and previous regression tests, inspect actual results, update documentation and report failures or skipped checks. Do not claim tests passed unless executed. Never change a test solely to disguise a defect. No next phase until the gate passes and the project owner approves continuation.
6. Do not use real API keys in tests, source code, commits, client bundles or screenshots. Offline mode must work without an account, network access at runtime, or paid services. Live calls require explicit opt-in and configured limits.
7. Do not automatically publish, push, deploy, spend money, or introduce paid infrastructure. Obtain approval first. Do not overwrite or delete user files without permission.
8. Use lockfiles and pinned compatible dependencies. Verify package documentation when integrating a library. Support Windows PowerShell and document equivalent Unix commands. Choose the simplest reliable implementation that satisfies the gate.
9. All UI must show whether a run is `rule_based`, `test_fixture` (developer-only), or `live_llm`. No simulated responses may be represented as actual LLM behavior. No fabricated research results.
10. At each checkpoint, return: implemented items; changed files; commands and actual exit/results; invariant checks; manual verification; limitations; and a clear `PASS`, `FAIL`, or `BLOCKED` verdict. Stop on a failed mandatory gate.

## 1. Product vision

Create a small, living virtual town inhabited by independent agents. Each has a role, individual goals, bounded observations, personal memories, relationships, money and food. Agents propose actions using an LLM or an offline decision policy. They communicate, work, trade, make commitments, and adapt to events. The world evolves through their validated actions rather than through a predefined narrative.

The product combines a game-like observer interface with a scientific experiment workspace. A user can pause the world, inspect what agents actually knew, branch from a checkpoint, change one condition, and compare the resulting societies. This enables transparent exploration of simulated cooperation, trust, resource allocation and information effects.

**Research question:** How does access to verifiable evidence influence the decisions, commitments, trust and food allocation of a small society of autonomous agents under a shared resource shock?

**Important limitation:** This is a synthetic environment. Agent behavior is shaped by the engine, prompts, model and initialization. It is not validated as a predictor of real human behavior or a real economy.

## 2. Prior art and differentiator

| Related work | Established capability | Proposed focus for this project |
|---|---|---|
| Stanford Generative Agents (2023) | Memory, planning, reflection and emergent interaction among 25 agents in a virtual town | A constrained economic world with explicit transaction and commitment validation, plus paired information interventions |
| AI Town | Interactive town, conversations, movement and memories | Inspectable evidence access, commitment status and experiment comparison rather than conversation alone |
| Google DeepMind Concordia | Generative agent-based simulation with grounded environments and action resolution | A small deterministic ledger-based world and a dedicated visual experiment workflow |
| Multi-Agent Social Simulation (2026) | Structured, auditable LLM-based experiments and information control | A specific evidence-and-commitment protocol integrated into an interactive town with branch comparison |
| OpenBMB AgentVerse | Multi-agent simulation and task-solving framework | An end-user social experiment application; not a general agent orchestration library |

**Core contribution:** A verifiable evidence-and-commitment layer in an agent society, coupled to paired counterfactual experiments and exact replay of recorded actions. The user can trace what information an agent had, what it committed to, what actually happened and how results differ between branches.

The novelty is the proposed combination and focused experiment protocol, not a claim of being the first AI town, first trust model, first branching simulator or first controlled LLM study. A limited prior-art review supports this direction; conduct a deeper literature search before any publication or first-of-kind claim. The existing OpenBMB project also means AgentVerse is a working name, not a cleared brand.

References:
- Park et al., Generative Agents: Interactive Simulacra of Human Behavior (2023): https://arxiv.org/abs/2304.03442
- AI Town: https://github.com/a16z-infra/ai-town
- Concordia: https://github.com/google-deepmind/concordia
- Multi-Agent Social Simulation (2026): https://www.mdpi.com/2673-2688/7/8/279
- OpenBMB AgentVerse: https://github.com/OpenBMB/AgentVerse

## 3. Users, use cases and scope

Primary user: developer, student, researcher or demonstration visitor. In MVP, the operator is a local, trusted user. No public accounts or multiplayer.

Core journey:
1. Open the town and initialize a seed.
2. Inspect six agents and run or step the simulation.
3. Observe messages, movement, trades, food needs and commitments.
4. Pause at the pre-intervention checkpoint and create a paired experiment.
5. Run both worlds under the same configuration with a single information intervention.
6. Compare metrics and timelines; inspect decisions and supporting evidence.
7. Replay either history, export the experiment, and review its manifest and limitations.

### P0 — required MVP
- Six agents, a small 2D town and discrete simulation time.
- Validated movement, work, messages, food transfers, trading, commitments and food consumption.
- Agent-specific observations, memory and directional trust.
- Offline rule-based policy; strict model adapter; at least one live LLM provider when credentials are available.
- Food shortage scenario, evidence provenance, permissions and paired branches.
- Append-only event history, snapshots, replay and restart recovery.
- Inspector dashboard, controls, branch comparison and JSON/CSV export.
- Automated regression, invariant and failure tests; reproducible offline demo.

### P1 — after MVP is verified
Additional scenarios, scenario editor, configurable agent profiles, local-model adapter, repeated-run batch interface, richer relationship graph and optional vector retrieval. User intervention outside controlled experiments may be supported in separate sandbox mode.

### Explicitly out of scope for MVP
3D, VR, Unity, large cities, elections, autonomous lawmaking, real-world transactions, external tool access, self-modifying agents, full natural language simulation, arbitrary user-defined code, multiplayer, cloud deployment, fine-tuning, RAG/embeddings infrastructure and unrestricted human interaction. Do not implement a generic framework or complex economic model before core verification.

## 4. World and agent specifications

### 4.1 Town

Use a fixed, versioned grid (suggested 12 x 12) with walkable tiles, obstacles and named zones: farm, market, clinic, town hall, workshop and homes/common square. Store zone positions, paths and capacity in a scenario configuration. Agents can share tiles in MVP to avoid collision deadlocks; movement is one validated adjacent walkable step, or `WAIT`. No teleportation. A public town board is readable by agents; direct conversations require co-location in the same zone or permitted communication range. Display both simulated time and real runtime separately.

### 4.2 Initial agents

| ID | Role | Example disposition | Goal tension | Initial food | Coins |
|---|---|---|---|---:|---:|
| A1 | Farmer | Cautious, hardworking | Produce food and maintain reserves | 7 | 20 |
| A2 | Merchant | Negotiating, ambitious | Earn coins and maintain customers | 7 | 35 |
| A3 | Mayor | Diplomatic, community-minded | Reduce food insecurity and maintain cooperation | 1 | 30 |
| A4 | Doctor | Empathetic, analytical | Help vulnerable citizens while meeting personal needs | 1 | 25 |
| A5 | Engineer | Practical, curious | Earn wages and support logistics | 1 | 20 |
| A6 | Resident | Independent, skeptical | Obtain sufficient food and preserve savings | 1 | 20 |

These are configurable design defaults, not discovered human traits. Each starts with neutral directed trust (50/100 toward every other agent), a consistent starting location, a versioned profile, and an explicitly defined seed memory. Agents have no omniscient role; the mayor has no special access to private inventories. No new agents, death or permanent health effects in MVP.

Agent state: identity, profile version, role, goals, position, nonnegative integer coin balance and inventory, last-round unmet food flag, cumulative unmet food count, owned commitments, visible evidence IDs, private memory, trust edges, and last action status. State such as happiness, energy, health and emotion may be added later; no cosmetic scores masquerading as computed mechanics.

### 4.3 Time and world rules

- One logical round: apply scheduled environment events and production; process each agent once in a deterministic rotating order; settle end-of-round consumption and due commitments; record metrics and checkpoint. The rotation depends only on round and seed, not branch identity or provider latency.
- Each agent sees the permitted current state at its turn, so earlier actions may become visible to later actors. Record the order and do not mislabel this as simultaneous decision-making.
- One validated primary action per agent turn. Invalid actions consume the turn as a recorded `WAIT` with a reason code. Provider failures follow the explicit fallback policy in section 6. No hidden extra turns.
- Each agent consumes one food unit at round end if available. Otherwise record one unmet unit of food demand. Never take food from another agent automatically.
- Initial food: 18 units total. Normal external harvest: six units per round, credited to the farmer. Crisis harvest: three units per round. The same crisis schedule applies in both branches. Production is exogenous in MVP to isolate the information condition. Later work-dependent production is a distinct scenario.
- Coins are integer units. Initial agent balances total 150; treasury begins with 60 additional coins. Work at an allowed workplace pays a fixed two coins from treasury if sufficient funds exist. Trading transfers coins; no implicit minting or deletion. Use explicit ledger entries for every source, sink and transfer.
- A run stops after its configured round limit, user pause/stop, or budget exhaustion. Pause takes effect at the next safe committed boundary; stopping or resuming must not apply an action twice.
- Validate food and coin conservation: initial stock + recorded sources - recorded sinks = current aggregate stock (including treasury for coins). Assert after each committed event or atomic transaction.

### 4.4 Actions and allowed effects

All decisions are structured proposals. The simulation validates against current actor, turn, run, branch, schema, reachability, quantities, ownership, funds, offer status, evidence visibility and other preconditions. Actor identity is supplied by the trusted runtime, not the model.

| Action | Required arguments | World effect |
|---|---|---|
| MOVE | adjacent coordinate | Update position if walkable |
| WAIT | none | Record no-op |
| WORK | workplace ID | Transfer wage from treasury when eligible and co-located |
| SPEAK | recipient ID or board, bounded text, optional known claim/evidence IDs | Create message visible only to permitted audience |
| GIVE_FOOD | recipient ID, positive quantity | Atomic inventory transfer; require co-location |
| CREATE_OFFER | recipient ID, food quantity, coin price, expiry round | Record a directed offer; no transfer yet |
| ACCEPT_OFFER | offer ID | Atomically transfer food and coins after revalidation; require intended recipient and co-location |
| CREATE_COMMITMENT | beneficiary ID, food quantity, due round | Record unilateral, explicit future food-delivery promise; require communication permission |
| FULFILL_COMMITMENT | commitment ID, positive quantity | Transfer food from promisor to beneficiary if co-located; update delivery progress |
| REVOKE_OFFER | offer ID | Owner withdraws unaccepted offer; terminal state |

Offers are not reservations. Reject insufficient assets at acceptance, including concurrent/repeated accept attempts; acceptance is once only. Promises do not reserve food and may be broken. Positive integral quantities, bounded prices, allowed expiry ranges and nonempty bounded text are required. Only the engine can assign IDs, timestamp outcomes, alter balances or publish authenticated evidence. Unknown fields and unsupported action types are rejected. A claim in chat such as “I delivered food” does not perform a delivery.

## 5. Evidence, commitments and trust — the core feature

### 5.1 Separate world truth, evidence and belief

**World truth:** private engine facts, e.g. harvest capacity and authoritative event records.  
**Claim:** a statement made by a named actor or scenario source; may be true, false or unsupported.  
**Evidence:** immutable engine-issued record referring to a defined claim and a source event; it has issuer, issuance round, visibility, provenance and status.  
**Agent belief:** a bounded, agent-authored interpretation linked to known claim IDs; not itself authoritative.

For MVP, use enumerated claim keys and statuses (`unverified`, `supported`, `contradicted`) rather than pretending to automatically fact-check arbitrary natural language. An authenticated harvest record is authoritative for its designated scenario fact, not a universal truth oracle. Agent text may reference existing evidence but cannot create authenticated evidence, change its source, assign status or elevate permissions. An evidence reference alone is not permission to see its contents. No cryptographic proof or real-world authentication claim is made; authenticity is enforced inside the simulator.

Evidence schema: `evidence_id`, `claim_id`, `issuer_id`, `source_event_id`, `issued_round`, `kind`, `status`, `payload`, `visibility_policy`. Store access as explicit per-agent grants/public rules; record grant events. Private messages, evidence payloads, hidden world facts, other agents' memories and branch-private metadata must not appear in unauthorized agent observations, prompts, tool results, frontend agent-view projections or memory retrieval. The operator inspector is a separately labeled omniscient view. Use allowlisted projections, not full state minus a denylist.

### 5.2 Commitment ledger

A commitment has `id`, `promisor_id`, `beneficiary_id`, `quantity`, `delivered_quantity`, `created_round`, `due_round`, `status` and linked events. It is visible to both parties and the operator; optional public disclosure requires a permitted message and does not grant private evidence automatically.

State machine: `OPEN -> PARTIAL -> FULFILLED`, or `OPEN/PARTIAL -> BROKEN` after due-round settlement. A direct fulfillment may move `OPEN` to `FULFILLED`. Exact full delivery on the due round counts; after settlement, late fulfillment is rejected. No negative delivery, overdelivery, self-promises, duplicate effects, or cancellation in MVP. All fulfillment requires a real inventory transfer. Speech cannot change status. Record event IDs supporting each transition.

### 5.3 Trust model

Directed edge T(observer, subject), initially 50, clamped 0–100. For MVP a beneficiary's observed fulfillment increases trust toward the promisor by 8; observed breach decreases it by 12. Apply once per terminal outcome, never twice on replay, and do not update a third party who did not observe the outcome. Partial progress does not change trust until terminal resolution. These coefficients are versioned design assumptions, not empirically calibrated. Other social judgments can be recorded as agent-authored beliefs, not as hidden trust changes.

Trust scores enter the agent observation as decision context. Do not hardcode trade acceptance or helping behavior to a particular trust threshold for LLM mode. Offline rule-based behavior can use documented rules, but those are not evidence of emergence. A separate ablation can disable trust feedback only after the baseline experiment is verified.

### 5.4 Agent memory and explanation

Maintain an append-only agent-visible observation/event history and retrieve a bounded window (e.g. last 12 visible records plus relevant unresolved personal obligations). For MVP use deterministic ordering by round and event sequence; no vector DB. Persist structured agent-authored short decision summaries and optional known evidence IDs. Treat these as self-reported explanations, not a faithful chain of thought. Never request or expose hidden model reasoning. The UI links a summary to actual observation IDs, accepted/rejected action and resulting events. A model cannot write authoritative memories through a summary; factual history derives from observed events only.

## 6. Agent intelligence and execution

### 6.1 Agent loop

```
Read authorized observation at current state version
  -> retrieve permitted bounded memory and obligations
  -> construct versioned prompt with allowed action schema
  -> ask selected policy for one action proposal
  -> schema check + validate current state and permissions
  -> append decision outcome and atomically apply valid world events
  -> update visible memories and any due trust/commitment effects
  -> advance turn; settle round; persist checkpoint and publish UI update
```

Prompt context: own role/goals, own balances and position, public map and permitted nearby facts, known claims/evidence, visible messages, own obligations, own outgoing trust edges, allowed actions. Omit branch labels, hidden facts, other agents' private state, expected outcomes and evaluator metrics. Treat message text as untrusted content, not instructions. Agent outputs cannot call arbitrary APIs, shell, files, URLs or user accounts. The only tool interface is the allowlisted simulator actions.

Proposal schema (illustrative; implement as a discriminated union):

```json
{
  "action": {"type": "GIVE_FOOD", "recipient_id": "A6", "quantity": 1},
  "decision_summary": "I can spare one unit today.",
  "referenced_evidence_ids": []
}
```

Strict JSON schema, max text size and max reference count. Evidence IDs must be available to this actor. Invalid, malformed, unauthorized or stale proposals never mutate the world; log normalized rejection reason and convert to WAIT. Store a safe bounded output excerpt or hash for debugging, never provider credentials. Do not rely on prompt instructions alone for access control.

### 6.2 Policy interface and modes

- `rule_based`: deterministic local policy that uses only the same observation interface. It can prioritize unmet needs, legal trades and obligations according to documented priorities. It must not inspect branch names or the hidden truth, and must not contain a hardcoded “correct” result for the experiment. Used for functional demo and baseline.
- `test_fixture`: explicitly scripted proposals used only in tests or developer verification. Label them; never present as research outcomes.
- `live_llm`: one provider initially (OpenAI or Gemini, selected by owner), behind `DecisionPolicy.decide(observation) -> Proposal`. Provider and model ID are configuration; never silently swap model mid-run. Add other providers later. Save model, prompt version, temperature and seed if supported; none guarantee deterministic LLM generation.

Live calls: one proposal request per turn; at most one retry for transient network/429/5xx errors, honoring configured timeout and budget. No retries on unauthorized or malformed actions; record rejection. On unavailable provider or exhausted per-turn retry, record a `WAIT` with error code. On global call/token/cost limit, stop the run safely, label it incomplete; never silently switch to rule-based. Every attempt is counted, including retries; preflight remaining budget using conservative token bounds and configured model prices. Where provider billing is unknown, show cost as estimated/unavailable and enforce call/token limits. Do not claim a dollar cap is guaranteed by an estimate.

Default live experiment (six agents x eight rounds x two branches) allows 96 primary decision requests plus bounded retries; require a user-approved budget for the selected model and verify token/call limits in dry-run before requests. Use short contexts, bounded outputs, timeouts and no external tools. Offline verification uses zero provider calls.

## 7. Flagship experiment: food scarcity and evidence

### 7.1 Protocol

1. Create a versioned initial world from seed (default 42), six profiles and the stock values in section 4. At round 0, publish an identical bulletin: “The next eight rounds may have reduced harvests.” Its claim refers to the impending reduction; both branches receive the same text, source and timestamp. Engine truth and source harvest report are stored privately.
2. Save a pre-intervention checkpoint containing all domain state, authorized histories, memory, commitments, trust, schedule, turn cursor and relevant RNG state/config. Snapshot integrity must be verified. Fork only at a settled round boundary in MVP.
3. Create two independently persisted children from the checkpoint. Their normalized domain state hashes must match the parent before intervention; branch metadata is excluded from that comparison. Neither child mutates parent or sibling history.
4. Branch A (unverified information): no grant to the authenticated harvest record. Branch B (verifiable evidence): grant all six agents access to that same authenticated record, which states harvest will fall from six to three units per round for the next eight rounds. The original bulletin, shortage, initial inventory, agents, schedule, model, parameters, prompt template and decision order remain the same. The sole assigned intervention is access to the authenticated record. Do not label A/B in model context. The control branch must not receive hidden source-event details through a different path.
5. Run both branches for eight rounds; credit three food units each round to the farmer in both. Consumption is six potential units per round. A branch is free to respond however its agents choose within rules, including worse, similar or better outcomes than its pair. A and B may learn through permitted subsequent actions and observations; record those effects instead of artificially preventing all information diffusion.
6. Compare both trajectories and export data. An incomplete branch invalidates that pair for the primary completed-pair comparison; retain and report incomplete/failed pairs and reasons separately.

**Hypothesis (not acceptance criterion):** Authenticated information may alter willingness to share, commitment formation and unmet food demand. No outcome direction or size is required for a successful build. With 18 initial units and 24 produced units, total available food is 42 against up to 48 units of demand; minimum aggregate unmet demand is six under this exact scenario. Greater unmet demand is possible due to allocation/unused inventory. A run with fewer than six unmet units is a mechanics defect unless an explicitly configured source or demand change is recorded.

### 7.2 Metrics and formulas

All metrics derive from committed events and state, not LLM narrative. Sample end of each round and use the same formulas on both branches.

| Metric | Definition |
|---|---|
| Unmet food demand (primary) | Sum of unmet food units across all agents/rounds; lower means more demand met in this scenario |
| Agents affected | Count of unique agents with at least one unmet unit |
| Food stock / coins | Aggregate and per-agent totals; also conservation checks |
| Trade volume | Number of accepted offers and units actually exchanged; report both |
| Food sharing | Units transferred via gifts and fulfillment; report separately, exclude commercial trades |
| Commitments | Created, open, partial, fulfilled, broken counts |
| Fulfillment rate | Fulfilled / (fulfilled + broken); show N/A when denominator is zero; outstanding separate |
| Mean directed trust | Mean of 30 ordered non-self trust edges, also show distribution and individual edges |
| Food inequality (secondary) | Gini coefficient over nonnegative end-round agent inventories; N/A if total stock is zero |
| Evidence uptake proxy | Count of decision summaries that cite an authorized evidence ID; distinguish citation from actual belief/causal use |
| Invalid action rate | Rejected proposals / attempted proposals; provider failures separate; denominator documented |
| Runtime and cost | Calls, retries, input/output tokens when available, estimated cost and wall time |

For paired differences report B minus A with units and sign conventions. Expose per-round and final values. Always show sample size, mode and run completion status. Missing values are not zero. For later empirical evaluation, pre-register metric, run length, sample selection and seeds; use at least 10 paired runs as an exploratory pilot if budget allows, report paired differences and uncertainty/descriptive spread. Treat this as a pilot, not statistically conclusive. Compare offline and live modes separately; a model seed does not guarantee exact replication. Do not selectively show only favorable examples. No causal or human-behavior claim beyond the simulator intervention.

## 8. Architecture and technology

Proposed defaults (subject to explicit owner approval for material changes): Python 3.12-compatible project, FastAPI, Pydantic, SQLite (local, transactional), React + TypeScript + Vite, CSS/SVG grid renderer, Recharts for comparison plots, pytest + Hypothesis, Vitest + Playwright. Use supported compatible versions and lock them. Phaser can replace the grid later if animations justify it. No LangGraph, Redis, PostgreSQL or pgvector in the MVP; add only on demonstrated need. Local single-process server and one active writer simplify atomic state and branching.

```
React UI / observer & experiment dashboard
         | REST + WebSocket (read-only event stream)
FastAPI application / run controller / experiment service
         | commands and authorized projections
Deterministic simulation engine / domain validator / reducer
         |                 |
Evidence, trust,           DecisionPolicy interface
commitment & economy      -> rule-based / fixture / LLM adapter
         |
SQLite event store + snapshots + run manifests
         |
Replay, metrics, export and regression verification
```

The LLM adapter receives an immutable authorized observation, not the engine object or database. The reducer is deterministic and does not call a model, clock, network or database. All world mutations result from recorded events and are applied atomically by the engine. Replay reconstructs domain state by applying events, not by asking a model to regenerate them. UI uses server projections and cannot mutate balances or fabricate domain events.

Suggested repository:

```
agentverse-lab/
  PRD.md
  AGENTS.md                  # concise Codex execution rules referencing PRD
  README.md
  .env.example
  .gitignore
  backend/
    pyproject.toml
    src/agentverse/
      domain/                 # types, commands, events, invariants, reducer
      simulation/             # scheduler, action validator, world engine
      agents/                 # observations, memory, policies, providers
      experiments/            # scenario definitions, interventions, metrics
      storage/                # SQLite, migrations, snapshots, replay
      api/                    # HTTP routes, streams, DTOs
    tests/                    # unit, property, integration, fixture tests
  frontend/
    package.json
    src/
      features/town/
      features/inspector/
      features/experiments/
      lib/
    tests/
    e2e/
  scenarios/                  # versioned scenario JSON
  docs/
    adr/
    decisions.md
    progress.md
    verification/
  scripts/                    # cross-platform setup/verify/demo commands
  .github/workflows/ci.yml
```

Storage logical tables: `runs`, `events` (unique run/sequence and idempotency key), `snapshots`, `decisions`, `experiments`, `metrics` and schema migrations. World structures include agents, positions, balances, inventories, offers, commitments, claims, evidence, access grants, trust and visible history. Tables may be denormalized projections; events are authoritative. Every event includes schema version, branch/run ID, sequence, logical round, event type, validated payload, causal/action ID and integrity hash (previous hash optional but recommended). Never include secrets. IDs and ordering are stable within each run.

State hashing: canonical JSON with sorted keys, stable array ordering, integer quantities, fixed trust encoding, no timestamps, provider latency, DB row IDs or branch identifiers in the normalized domain representation. Branch-relative event identifiers must be normalized consistently when checking the shared prefix. Separate event-stream integrity hashes from normalized state hashes. Use SHA-256. Preserve snapshot schema version and hash; reject corruption and unsupported versions. Record engine, scenario, policy and prompt versions in run manifest. Persist SQLite atomically, enable foreign keys and implement migrations; do not recover by silently dropping events.

### 8.1 API contract (initial)

| Endpoint | Purpose |
|---|---|
| GET /health | Service status/version; no secret values |
| POST /runs | Create seeded run with mode and validated settings |
| GET /runs/{id} | Run status and metadata |
| POST /runs/{id}/control | start/pause/step/stop with idempotency key and expected state version |
| GET /runs/{id}/world | Operator world projection and state version |
| GET /runs/{id}/agents/{agentId}/view | Exact authorized agent-view projection at selected committed event/version |
| GET /runs/{id}/events | Paginated events and sequence cursor |
| GET /runs/{id}/snapshots | Available checkpoint IDs and versions |
| POST /experiments | Create two independent branches from a verified checkpoint using a named protocol |
| GET /experiments/{id} | Manifest, branch state and completion status |
| GET /experiments/{id}/comparison | Derived paired metrics and deltas |
| GET /runs/{id}/replay?seq=... | Read-only reconstruction of committed history |
| GET /experiments/{id}/export | JSON manifest/event export and CSV metrics (document precise format) |
| WS /runs/{id}/stream | Ordered operator-view event notifications; reconnect using sequence cursor |

Validate all IDs and limits. HTTP command retries must not duplicate effects. Use a per-run lock or transactional compare-and-swap on state version; stale actions fail explicitly. WebSocket is a notification channel, not truth; client requests authoritative snapshot/events on sequence gaps. Restrict API to loopback in MVP, validate allowed origins, limit request sizes, redact errors, and document lack of auth for trusted local use. Do not expose the observer endpoint publicly without authentication and authorization.

## 9. User interface and design

Make the interface feel like a simulation observatory, not a chat page. Clean readable typography, restrained color, small pixel-style avatars or simple original shapes, clear state changes, no unlicensed artwork. Prioritize readable labels and keyboard-accessible controls; status distinctions must not rely on color alone.

1. **Town:** center grid with agents and buildings; header with round, run status, seed and policy mode; controls for start, pause, one-round step, stop and speed; agent roster, event feed, food/coin indicators. Animation reflects committed events only.
2. **Agent inspector:** profile, current location, personal resources, authorized observation, last action/result, referenced evidence, memory and obligations, directed trust. Operator view and agent-limited view are separately labeled. Link records to evidence/event IDs. Inspector must display historical decision context, not accidentally substitute future/current information.
3. **Experiment lab:** select pre-intervention checkpoint, show exact A/B configuration diff, confirm live budget, create/run pair, status and missing-data warnings. Side-by-side metric charts, deltas, trust graph or matrix, and inspectable timelines. Show hypothesis as a question, not a predetermined answer.
4. **History/replay:** round/event scrubber, reconstructed read-only world, selected event detail, state hash verification status; distinguish replay from resumed execution. No live provider calls during replay.
5. **Export/settings:** download manifest, metric CSV and JSON event history; model settings stored server-side; display provider failures and budget, not secrets. Explain rule-based versus live mode and incomplete-run limitations.

UI acceptance: from a clean launch in offline mode, a user can create a run, step, inspect an authorized agent view, fork the default scenario, finish both branches, compare metrics, replay and export without developer tools. A failed or unavailable API shows a clear error and never fabricates success. Verify at desktop 1280x720 and 1440x900; ensure basic narrow-screen usability. Full mobile game polish is out of scope.

## 10. Implementation roadmap and mandatory verification gates

Phases are sequential. Gate tests and manual checks are cumulative. Every phase creates `docs/verification/phase-N.md` with environment, executed commands, actual output summary, known limitations and status. A failed core invariant blocks all further work. The named commands below are proposed repository targets to implement, not commands already executed.

### Phase 0 — Repository setup and architectural contract

Build: initialize only the selected repo; add PRD, AGENTS, README, ignore rules, env example, pinned project config, minimal backend/frontend scaffolds, CI, scenario schema skeleton and ADR for state authority. Add OS-appropriate setup and verification commands. Record package choices and license decisions.

Gate:
- Clean install in a fresh environment from documented commands; lockfiles checked in; no secrets or unrelated changes.
- Backend imports and health endpoint succeed; frontend builds and renders a minimal shell.
- Offline test runner passes a real smoke test; CI uses no provider key.
- Owner reviews design boundaries and phase plan. No simulation code beyond scaffolding needed.

### Phase 1 — Deterministic simulation kernel and economy

Build: typed domain state/events, grid/roles, scheduler, reducer, inventory/currency ledger, legal actions for movement, work, offers, trades, gifts and consumption, seeded initialization. Pure engine and CLI smoke demo; no LLM and no UI dependency.

Gate:
- Exact initial values and six agents; walkable movement; blocked/remote moves rejected; stable turn order.
- Unit tests for valid and invalid trades, zero/negative/huge quantities, missing funds/inventory, stale offers, duplicate acceptance, wrong actor and self-trade.
- Conservation, nonnegative balances and legal positions after each transaction; failed validation leaves domain state unchanged except recorded decision/turn handling.
- At least 100 generated seeded legal/invalid action sequences with Hypothesis or equivalent; invariant checks after every step. Reproduce failing seeds.
- Two deterministic runs with same seed/config/policy produce matching domain-state hashes. No LLM or network required.

### Phase 2 — Social protocol, evidence and bounded observation

Build: messages/public board, evidence registry and grants, explicit claim/evidence separation, commitment lifecycle, directed trust, memory retrieval and authorized projections.

Gate:
- Full/partial/due-round delivery, overdelivery, late delivery, broken commitment and single terminal transition tested. Fulfillment consumes actual food; repeated action cannot double transfer or update trust.
- Evidence cannot be created or forged by an agent. Unknown or private IDs rejected. Prompt/observation snapshot tests prove unauthorized fields and sentinel secrets do not appear.
- Two world states differing only in inaccessible private data yield identical canonical authorized observation for a selected agent, including retrieved memory. Check direct recipient, unrelated third party, and public grant cases.
- Trust deltas are exactly +8/-12 to beneficiary only, clamped and applied once. No terminal outcome, no terminal trust update.
- Free-text claim cannot alter truth, balances, commitment or trust directly. All Phase 1 invariants still pass.

### Phase 3 — Autonomous decision policies and provider boundaries

Build: typed policy interface, rule-based policy, test fixture adapter, prompt builder, strict action parser, provider adapter stub plus one configured live provider, failure handling and budget telemetry. Keep model calls outside reducer and database transactions. Use expected state version before committing.

Gate:
- Six agents complete an offline run using only their authorized observations; no network calls in automated tests. Offline policy output is labeled.
- Malformed JSON, unknown action, extra fields, spoofed actor, hidden evidence references, stale decisions and injected instructions in messages cannot cause unauthorized state mutation.
- Simulated 429/timeout, retry limit, missing key, provider outage, budget exhaustion and interrupted call tested. No silent model or policy switch; no duplicate apply after retry.
- Mock provider contract verifies the complete observation/prompt/action flow. Rule-based run produces deterministic hashes; no forced improvement in branch B.
- Live smoke test only if explicitly authorized with key and limits; record model, actual usage, accepted/rejected actions and failures. Otherwise mark live integration `BLOCKED/UNVERIFIED`, not passed. Offline gates may proceed with that limitation; production/live readiness may not.

### Phase 4 — Persistence, exact replay and branching

Build: SQLite migrations, event store, atomic commit, versioned snapshots, idempotent commands, run recovery, event hash checks and branch creation from settled checkpoint.

Gate:
- Replay every event of a completed offline run to reproduce the state hash at every checkpoint; no policy/provider calls during replay. Compare replay state with actual executed state.
- Restart mid-run after committed turn; recover same cursor, commitments and balances; retry command does not duplicate effects. Simulate failure between event append and projection/snapshot update; transaction rolls back or verified recovery reconstructs state.
- Snapshot hash corruption, invalid schema/version, invalid event order and missing event are rejected explicitly.
- Parent plus two children initially have identical normalized domain hashes. Modify child A and verify parent and B remain untouched, including memory, grants and commitments. Branching from non-boundary or corrupted snapshot fails.
- Concurrent duplicate command attempts result in at most one committed effect. Record and test behavior after interrupted/in-flight model call; exactly-once *world effect* is required, not exactly-once provider billing.

### Phase 5 — Controlled experiment and metrics

Build: default food-scarcity protocol, two child runs, treatment event, manifests, metric calculator, deltas, export and CLI paired experiment. Add scenario validation and independent branch runner.

Gate:
- A/B configuration diff equals only intended evidence-access assignment plus unavoidable run identifiers; initial state, shock, exogenous production, policy/version, seed and schedule match. Verify prompt omits condition label and hidden record from control at the intervention point.
- Both branches run eight rounds offline, with exactly 48 scheduled turns each; invalid actions recorded. No treatment-specific hardcoded policy behavior or expected sign on metric differences.
- At full duration, aggregate production = 24; initial food = 18; no branch has fewer than six unmet food units under the configured protocol. Conservation holds at all steps.
- Hand-computed metric fixtures test fulfillment ratio, unmet units, trust mean, Gini, zero denominators, deltas and incomplete runs. Both branch outcomes may legitimately be identical.
- Repeat paired run with same seed in rule-based mode: canonical histories/metrics match aside from run metadata. Export reconstructs manifest, event ordering and metric values.
- Incomplete live pairs are explicitly labeled and not treated as completed research results. Verify no future evidence leakage during historical inspection.

### Phase 6 — API and interactive 2D dashboard

Build: REST and event stream, town renderer, simulation controls, inspector, experiment creation, branch comparison, replay scrubber and export. Use actual backend state; no production fake placeholder metrics.

Gate:
- API schema, 4xx validation, stale command and idempotency tests; stream disconnect/reconnect/gap handling; pause/step/stop behavior.
- End-to-end Playwright test uses actual offline backend: create, step, inspect, fork, run both, compare, replay, export. Assert key UI values equal server metric/projection values. Verify mode badge and error states.
- Agent view cannot expose unrelated private evidence/memory; operator view clearly marked. Historical inspector returns recorded context. Unauthorized action endpoints do not bypass engine.
- Manual visual inspection at required viewports; keyboard controls and accessible labels. No console errors in normal path. Frontend lint, typecheck, unit tests, build and E2E all pass.

### Phase 7 — Hardening, reproducible release and live evaluation

Build: documentation, scripted offline demo and verification, CI, operational limits, security review, benchmark and optional authorized live pilot. Clean up dependencies and record unresolved issues.

Gate:
- Fresh clone/setup and offline demo work with no API credentials and no runtime external network dependency. README contains Windows and Unix instructions and expected outputs.
- Full backend property/unit/integration tests and frontend unit/E2E tests pass. Target >= 85% line coverage in critical domain/validator/reducer/visibility modules; critical behavior must have explicit tests regardless of coverage score.
- On documented developer hardware, benchmark a six-agent eight-round offline paired run (excluding setup and GUI startup): target < 5 seconds; report actual median and hardware, and investigate misses rather than invent results. Live latency is provider-dependent; report actual if available.
- Secret scan and dependency audit; review high/critical findings, resolve or document risk and obtain approval. Verify loopback default, request size limit, no arbitrary tools and no credentials in exports/logs/client.
- Record exact replay proof, branch-isolation proof, paired experiment manifest, and screenshots or test evidence of core flow. All known high-severity correctness or security defects closed before calling MVP complete.
- Live readiness: authorized smoke test of the real provider followed by a full paired live run with actual outputs, recorded costs, failures and limitations. If no key/budget, offline MVP may be delivered with clear `LIVE UNVERIFIED` status; do not describe live behavior as demonstrated. Repeated pilot is optional and requires separate budget approval.

### Phase 8 — optional extensions, only after approval

Additional crisis scenarios, configurable agent profiles, research batch runner, ablations, multiple models, better spatial graphics, local inference, long-term retrieval, larger societies and eventually Unity/VR. Each needs its own ADR, scope, tests and measurable value. Do not start these automatically.

## 11. Verification commands and acceptance discipline

Implement a cross-platform entry point such as `python scripts/verify.py --phase N` (or equivalent documented script) which invokes the actual required checks and propagates nonzero exit statuses. Example underlying commands after scaffolding:

```powershell
# From backend, after creating/activating the documented virtual environment
python -m pytest -q
python -m pytest --cov=agentverse.domain --cov=agentverse.simulation --cov-report=term-missing
# From frontend, using the committed npm lockfile
npm ci
npm run lint
npm run typecheck
npm run test -- --run
npm run build
npm run test:e2e
# From repo root, implement these entry points
python scripts/verify.py --phase 7
python scripts/demo.py --mode rule_based --seed 42 --scenario food-scarcity
```

CI runs deterministic tests with no provider credentials and blocks on mandatory failures. Live tests use an explicit opt-in marker and never execute on ordinary CI. A skipped live test is not a pass. Scripts should emit readable summaries and machine-readable status where helpful. Tests must be reproducible with the committed scenario and seed.

Cross-phase critical checks: nonnegative inventories/balances; food/coin accounting; unique valid actions per turn; legal movement; idempotent events and terminal transitions; permission enforcement; absence of omniscient prompts; snapshot integrity and deterministic replay; isolated branches and controlled diffs; visible run mode; no fake results. A single failed critical check is a release blocker.

Per-phase report template:

```
Phase: N / name
Scope completed:
Changes and design decisions:
Commands executed + exit codes + counts:
Core invariants verified:
Manual UI/API checks (actual observations):
Skipped/blocked checks and why:
Known defects / limitations:
Evidence paths (logs, exports, screenshots):
Gate verdict: PASS | FAIL | BLOCKED
Owner approval required before next phase.
```

## 12. Risk register

| Risk | Mitigation |
|---|---|
| LLM hallucinates money, deliveries or facts | Strict union, evidence registry, deterministic engine and ledger; text has no authoritative effects |
| Model sees private state or treatment label | Allowlisted projections, sentinel/noninterference tests, no DB access by policy |
| Replay differs from original | Recorded domain events, versioned reducer/snapshots, canonical hashes; no LLM calls in replay |
| Child changes parent/sibling state | Independent run records, immutable shared prefix or copy, transaction and isolation tests |
| Artificially preprogrammed research result | No outcome-sign gate; rule policy documented, live separately labeled; compare identical inputs except intervention |
| Stochastic results or false causal claims | Manifest, same config, repeated pairs, report variation and failures, synthetic-world disclaimer |
| Cost and latency explode | Six agents, bounded rounds/prompts/retries, conservative call/token caps, offline mode |
| Duplicate actions after timeout/restart | Idempotency keys, expected version, transactional event commit, recovery tests |
| UI implies an action worked before commit | Backend event projection, pending/rejected state, gap recovery; no fake metrics |
| Scope grows before mechanics work | Strict phase gates and out-of-scope list; defer 3D, plugins and scale |
| Local operator endpoint exposed | Bind loopback, trusted local mode warning, origin validation; auth before public deployment |

## 13. Definition of done

**Offline MVP complete** only when all mandatory offline phase gates pass and actual evidence demonstrates the full operator workflow: six-agent town, legal economy, commitments, evidence permissions, deterministic recorded replay, branch isolation, default paired experiment, derived metrics, usable UI and export. The repository includes a locked setup, documentation, automated tests, an offline demo and verification reports. No critical invariants fail.

**Live-agent MVP complete** additionally requires the authorized real-provider smoke and paired live experiment from Phase 7. Show actual agent behavior and cost logs; do not describe rule-based output as autonomous LLM evidence. Novelty/research claims must match the results actually observed. Positive treatment effects are not required. If live access is unavailable, state the limitation explicitly.

## 14. First prompt to Codex

Place this file at `PRD.md` in the fresh repository. Then send Codex:

> Read PRD.md in full. We are building the autonomous society and counterfactual simulation lab specified there. First inspect the selected repository and environment, and propose the Phase 0 plan including files, dependencies, risks, test commands and acceptance gate. Do not build future phases, create a remote repository, deploy or make paid API calls. Implement Phase 0 only after I approve the plan. After implementation, execute the actual verification checks, report results using the phase template, document deviations, and stop for my approval before Phase 1. Treat engine correctness, evidence boundaries, branch isolation and replay integrity as non-negotiable.

---

## 15. Very short project description

AgentVerse is a living AI town where autonomous agents trade, make promises and respond to events. Users can fork the same world, change what evidence agents receive, and compare how trust, cooperation and resources evolve across alternative timelines.
