from dataclasses import dataclass, replace
from threading import RLock

from pydantic import ValidationError

from agentverse.domain.actions import proposal_schema
from agentverse.domain.model import TREASURY, Agent, Entry, Event, World
from agentverse.domain.reducer import check_invariants, reduce_event
from agentverse.experiments.town import TownScenario
from .economy import Rejection, resolve


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
        if any(a.id == TREASURY for a in agents):
            raise ValueError("agent ID collides with treasury")
        self._state = World(config, seed, agents, config.treasury)
        check_invariants(self._state)
        self._run_id = run_id
        self._events: list[Event] = []
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
        self._state = updated
        return event

    def start_round(self) -> Event:
        with self._lock:
            w = self._state
            if w.stage != "ready":
                raise ValueError("round cannot start at this boundary")
            count = w.scenario.harvest[w.round]
            entries = (Entry("food", None, w.scenario.farmer_id, count),) if count else ()
            return self._commit(Event(w.version + 1, w.round + 1, "ROUND_STARTED", entries=entries))

    def submit(self, turn: Turn, payload: object) -> Event:
        with self._lock:
            if turn != self.turn:
                raise TurnConflict("stale or mismatched turn")
            w = self._state
            try:
                if not isinstance(payload, dict):
                    raise Rejection("invalid_schema")
                action = proposal_schema.validate_python(payload)
                event = resolve(w, turn.actor, action)
            except ValidationError:
                event = Event(w.version + 1, w.round, "WAIT", turn.actor, "invalid_schema")
            except Rejection as error:
                event = Event(w.version + 1, w.round, "WAIT", turn.actor, str(error))
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
            return self._commit(Event(w.version + 1, w.round, "ROUND_SETTLED",
                                      entries=meals, hungry=hungry, offers=expired))
