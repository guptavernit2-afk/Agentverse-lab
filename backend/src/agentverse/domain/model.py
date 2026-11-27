from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Literal

from agentverse.experiments.town import Position, TownScenario
from .social import Claim, Commitment, DecisionNote, Evidence, Grant, Message, SocialState

Asset = Literal["food", "coins"]
EventKind = Literal["ROUND_STARTED", "ROUND_SETTLED", "WAIT", "MOVE", "WORK",
                    "GIVE_FOOD", "CREATE_OFFER", "ACCEPT_OFFER", "REVOKE_OFFER",
                    "SPEAK", "CREATE_COMMITMENT", "FULFILL_COMMITMENT",
                    "CLAIM_PUBLISHED", "HARVEST_RECORDED", "EVIDENCE_GRANTED"]
TREASURY = "@treasury"


@dataclass(frozen=True)
class Agent:
    id: str
    position: Position
    food: int
    coins: int
    unmet: int = 0
    last_unmet: bool = False
    last_action: EventKind | None = None
    last_rejection: str | None = None


@dataclass(frozen=True)
class Offer:
    id: str
    seller: str
    buyer: str
    quantity: int
    price: int
    expiry_round: int
    status: Literal["open", "accepted", "revoked", "expired"] = "open"


@dataclass(frozen=True)
class Entry:
    asset: Asset
    source: str | None
    destination: str | None
    amount: int


@dataclass(frozen=True)
class Event:
    sequence: int
    round: int
    kind: EventKind
    actor: str | None = None
    reason: str | None = None
    entries: tuple[Entry, ...] = ()
    position: Position | None = None
    offers: tuple[Offer, ...] = ()
    hungry: tuple[str, ...] = ()
    claim: Claim | None = None
    evidence: Evidence | None = None
    source_id: str | None = None
    grant: Grant | None = None
    message: Message | None = None
    commitments: tuple[Commitment, ...] = ()
    note: DecisionNote | None = None


@dataclass(frozen=True)
class World:
    scenario: TownScenario
    seed: int
    agents: tuple[Agent, ...]
    treasury: int
    offers: tuple[Offer, ...] = ()
    round: int = 0
    cursor: int = 0
    stage: Literal["ready", "acting", "settlement", "finished"] = "ready"
    version: int = 0
    produced: int = 0
    consumed: int = 0
    social: SocialState = SocialState()

    def agent(self, agent_id: str) -> Agent:
        return next(agent for agent in self.agents if agent.id == agent_id)

    def order(self) -> tuple[str, ...]:
        ids = tuple(agent.id for agent in self.agents)
        offset = (self.seed + self.round - 1) % len(ids)
        return ids[offset:] + ids[:offset]

    def canonical(self) -> str:
        data = {
            **vars(self),
            "scenario": self.scenario.model_dump(mode="json"),
            "agents": [asdict(agent) for agent in self.agents],
            "offers": [asdict(offer) for offer in self.offers],
            "social": asdict(self.social),
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)

    def digest(self) -> str:
        return sha256(self.canonical().encode("utf-8")).hexdigest()
