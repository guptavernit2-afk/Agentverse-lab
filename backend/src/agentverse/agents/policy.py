"""Decision policies see a frozen, actor-specific observation and propose one action."""
from collections.abc import Callable
from dataclasses import dataclass
import json
from typing import Annotated, Protocol

from pydantic import Field

from agentverse.domain.actions import Action, NoteInput, Proposal
from .observation import Observation


class Decision(Action):
    action: Annotated[Proposal, Field(discriminator="type")]
    note: NoteInput | None = None


class DecisionPolicy(Protocol):
    mode: str
    version: str

    def decide(self, observation: Observation) -> Decision: ...


class DecisionError(Exception):
    """Safe normalized reason for consuming one turn as WAIT."""


class BudgetExhausted(Exception):
    """The run is incomplete and its current turn is still available."""


def parse_decision(raw: str) -> Decision:
    def unique(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError("duplicate member")
        return result
    try:
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > 8192:
            raise DecisionError("invalid_schema")
        return Decision.model_validate(json.loads(raw, object_pairs_hook=unique))
    except (ValueError, RecursionError):
        raise DecisionError("invalid_schema") from None


class RulePolicy:
    mode = "rule_based"
    version = "town-priorities-1"

    def decide(self, observation: Observation) -> Decision:
        ctx = observation.as_dict()
        me = ctx["self"]
        nearby = {p["id"] for p in ctx["nearby"]}
        for promise in ctx["obligations"]:
            if promise["promisor"] == me["id"] and promise["beneficiary"] in nearby and me["food"]:
                qty = min(promise["quantity"] - promise["delivered"], me["food"])
                return Decision(action={"type": "FULFILL_COMMITMENT", "commitment_id": promise["id"], "quantity": qty})
        for offer in ctx["offers"]:
            if offer["buyer"] == me["id"] and offer["seller"] in nearby and offer["price"] <= me["coins"] and me["food"] <= 1:
                return Decision(action={"type": "ACCEPT_OFFER", "offer_id": offer["id"]})
        if me["food"] > 3 and nearby:
            return Decision(action={"type": "GIVE_FOOD", "recipient_id": min(nearby), "quantity": 1})
        tiles = next(z["tiles"] for z in ctx["map"]["zones"] if z["id"] == me["workplace"])
        if me["position"] in tiles:
            return Decision(action={"type": "WORK", "workplace": me["workplace"]})
        return Decision(action={"type": "WAIT"})


@dataclass
class FixturePolicy:
    propose: Callable[[Observation], str]
    mode = "test_fixture"
    version = "fixture-1"

    def decide(self, observation: Observation) -> Decision:
        return parse_decision(self.propose(observation))
