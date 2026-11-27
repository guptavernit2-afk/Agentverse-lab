from dataclasses import dataclass, replace
from threading import RLock

from pydantic import ValidationError

from agentverse.agents.observation import Observation, project
from agentverse.domain.actions import CreateCommitment, FulfillCommitment, Speak, proposal_schema
from agentverse.domain.model import TREASURY, Agent, Entry, Event, World
from agentverse.domain.reducer import check_invariants, reduce_event
from agentverse.domain.social import BOARD, Claim, Evidence, Grant, SocialState, TrustEdge
from agentverse.experiments.town import TownScenario
from .economy import Rejection, resolve
from .social import decision_note, resolve_social


@dataclass(frozen=True)
class Turn:
    run_id: str
    version: int
    round: int
    actor: str


class TurnConflict(ValueError):
    """A submission identifies a different run, state version, or turn."""


class Kernel:
    def __init__(self, config: TownScenario, seed: int, *, run_id: str):
        if type(seed) is not int or not run_id:
            raise ValueError("an integer seed and a run identifier are required")
        agents = tuple(Agent(p.id, p.position, p.food, p.coins)
                       for p in sorted(config.profiles, key=lambda p: p.id))
        if any(a.id in (TREASURY, BOARD) for a in agents):
            raise ValueError("reserved agent ID")
        edges = tuple(TrustEdge(a.id, b.id) for a in agents for b in agents if a.id != b.id)
        self._state = World(config, seed, agents, config.treasury, social=SocialState(trust=edges))
        check_invariants(self._state)
        self._run_id = run_id
        self._events: list[Event] = []
        self._states = [self._state]
        self._lock = RLock()

    @property
    def state(self) -> World:
        with self._lock:
            return self._state

    @property
    def events(self) -> tuple[Event, ...]:
        with self._lock:
            return tuple(self._events)

    @property
    def turn(self) -> Turn:
        with self._lock:
            w = self._state
            if w.stage != "acting":
                raise TurnConflict("no active turn")
            return Turn(self._run_id, w.version, w.round, w.order()[w.cursor])

    def _commit(self, event: Event) -> Event:
        updated = reduce_event(self._state, event)
        self._events.append(event)
        self._states.append(updated)
        self._state = updated
        return event

    def observe(self, actor: str, *, version: int | None = None) -> Observation:
        with self._lock:
            index = self._state.version if version is None else version
            if type(index) is not int or not 0 <= index < len(self._states):
                raise ValueError("unknown committed version")
            world = self._states[index]
            if actor not in {a.id for a in world.agents}:
                raise ValueError("unknown agent")
            history = ((self._events[i], self._states[i + 1]) for i in range(index))
            return project(world, actor, history)

    def publish_harvest_claim(self) -> Event:
        with self._lock:
            w = self._state
            if w.social.claims:
                raise ValueError("harvest claim already published")
            claim = Claim("claim-harvest", "reduced_harvest", "town-board",
                          "Every scheduled round will produce fewer than six food units.")
            return self._commit(Event(w.version + 1, w.round, "CLAIM_PUBLISHED", claim=claim))

    def issue_harvest_record(self) -> Event:
        with self._lock:
            w = self._state
            if not w.social.claims or w.social.evidence:
                raise ValueError("expected a published claim without an issued record")
            schedule = w.scenario.harvest
            status = "supported" if all(amount < 6 for amount in schedule) else "contradicted"
            record = Evidence("evidence-harvest", w.social.claims[0].id, "harvest-register",
                              "harvest-source-1", w.round, "harvest_record", status, schedule)
            return self._commit(Event(w.version + 1, w.round, "HARVEST_RECORDED",
                                      source_id=record.source_event_id, evidence=record))

    def grant_evidence(self, evidence_id: str, *, grantee: str | None) -> Event:
        """Trusted scenario entry point. A null grantee makes the record public."""
        with self._lock:
            w = self._state
            if evidence_id not in {e.id for e in w.social.evidence}:
                raise ValueError("unknown evidence")
            if grantee is not None and grantee not in {a.id for a in w.agents}:
                raise ValueError("unknown grantee")
            grant = Grant(evidence_id, grantee)
            if grant in w.social.grants or Grant(evidence_id, None) in w.social.grants:
                raise ValueError("access already granted")
            return self._commit(Event(w.version + 1, w.round, "EVIDENCE_GRANTED", grant=grant))

    def start_round(self) -> Event:
        with self._lock:
            w = self._state
            if w.stage != "ready":
                raise ValueError("round cannot start at this boundary")
            count = w.scenario.harvest[w.round]
            entries = (Entry("food", None, w.scenario.farmer_id, count),) if count else ()
            return self._commit(Event(w.version + 1, w.round + 1, "ROUND_STARTED", entries=entries))

    def submit(self, turn: Turn, payload: object, *, note: object = None) -> Event:
        with self._lock:
            if turn != self.turn:
                raise TurnConflict("stale or mismatched turn")
            w = self._state
            report = None
            try:
                if not isinstance(payload, dict):
                    raise Rejection("invalid_schema")
                report = decision_note(w, turn.actor, note) if note is not None else None
                action = proposal_schema.validate_python(payload)
                if isinstance(action, (Speak, CreateCommitment, FulfillCommitment)):
                    event = resolve_social(w, turn.actor, action)
                else:
                    event = resolve(w, turn.actor, action)
            except ValidationError:
                event = Event(w.version + 1, w.round, "WAIT", turn.actor, "invalid_schema")
            except Rejection as error:
                event = Event(w.version + 1, w.round, "WAIT", turn.actor, str(error))
            if report is not None:
                event = replace(event, note=report)
            return self._commit(event)

    def settle_round(self) -> Event:
        with self._lock:
            w = self._state
            if w.stage != "settlement":
                raise ValueError("round must finish all turns before settlement")
            meals = tuple(Entry("food", a.id, None, 1) for a in w.agents if a.food)
            hungry = tuple(a.id for a in w.agents if not a.food)
            expired = tuple(replace(o, status="expired") for o in w.offers
                            if o.status == "open" and o.expiry_round == w.round)
            broken = tuple(replace(c, status="BROKEN", events=(*c.events, w.version + 1))
                           for c in w.social.commitments if c.outstanding and c.due_round == w.round)
            return self._commit(Event(w.version + 1, w.round, "ROUND_SETTLED",
                                      entries=meals, hungry=hungry, offers=expired, commitments=broken))
