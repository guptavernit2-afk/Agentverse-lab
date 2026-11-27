from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json

import pytest
from pydantic import ValidationError

from agentverse.domain.model import Entry
from agentverse.domain.reducer import reduce_event
from agentverse.experiments.town import TownScenario
from agentverse.simulation.kernel import Kernel, TurnConflict

WAIT = {"type": "WAIT"}


def active(town):
    kernel = Kernel(town, 42, run_id="kernel-test")
    kernel.start_round()
    return kernel


def advance(kernel, actor, round_number):
    while kernel.state.stage != "finished":
        if kernel.state.stage == "ready":
            kernel.start_round()
        elif kernel.state.stage == "settlement":
            kernel.settle_round()
        elif kernel.turn.actor == actor and kernel.turn.round == round_number:
            return
        else:
            kernel.submit(kernel.turn, WAIT)
    pytest.fail("requested turn was never reached")


def rejected(kernel, payload, reason):
    before = kernel.state
    event = kernel.submit(kernel.turn, payload)
    assert (event.kind, event.reason, event.entries) == ("WAIT", reason, ())
    after = kernel.state
    agents = tuple(replace(a, last_action="WAIT", last_rejection=reason) if a.id == event.actor else a
                   for a in before.agents)
    assert after == replace(before, agents=agents, version=before.version + 1, cursor=before.cursor + 1,
                            stage="settlement" if before.cursor == 5 else "acting")
    return event


def offer(kernel, **fields):
    payload = {"type": "CREATE_OFFER", "recipient_id": "A2", "quantity": 3,
               "price": 5, "expiry_round": 2, **fields}
    return kernel.submit(kernel.turn, payload).offers[0]


def accept(offer_id):
    return {"type": "ACCEPT_OFFER", "offer_id": offer_id}


def test_initial_state(town):
    world = Kernel(town, 42, run_id="initial").state
    assert [a.id for a in world.agents] == ["A1", "A2", "A3", "A4", "A5", "A6"]
    assert [p.role for p in town.profiles] == ["Farmer", "Merchant", "Mayor", "Doctor", "Engineer", "Resident"]
    assert [a.food for a in world.agents] == [7, 7, 1, 1, 1, 1]
    assert [a.coins for a in world.agents] == [20, 35, 30, 25, 20, 20]
    assert world.treasury == 60 and world.round == world.version == 0
    assert all(town.walkable(a.position) for a in world.agents)


def test_round_order_settlement_and_limit(town):
    kernel = Kernel(town, 42, run_id="wait")
    ids = tuple(a.id for a in kernel.state.agents)
    for offset in range(8):
        start = kernel.start_round()
        assert start.entries == (Entry("food", None, "A1", 6),)
        with pytest.raises(ValueError):
            kernel.start_round()
        with pytest.raises(ValueError):
            kernel.settle_round()
        seen = []
        for _ in ids:
            seen.append(kernel.turn.actor)
            kernel.submit(kernel.turn, WAIT)
        assert tuple(seen) == ids[offset % 6:] + ids[:offset % 6]
        kernel.settle_round()
        if offset == 1:
            assert [a.food for a in kernel.state.agents] == [17, 5, 0, 0, 0, 0]
            assert [a.unmet for a in kernel.state.agents] == [0, 0, 1, 1, 1, 1]
        with pytest.raises(ValueError):
            kernel.settle_round()
    assert kernel.state.stage == "finished"
    with pytest.raises(ValueError):
        kernel.start_round()
    assert len(kernel.events) == 8 * 8


def test_crisis_harvest_and_zero_stock(scenario_data):
    scenario_data["harvest"] = [3] * 8
    kernel = Kernel(TownScenario.model_validate_json(json.dumps(scenario_data)), 43, run_id="crisis")
    for _ in range(8):
        kernel.start_round()
        if kernel.state.round == 1:
            assert kernel.turn.actor == "A2"
        for _ in range(6):
            kernel.submit(kernel.turn, WAIT)
        kernel.settle_round()
    assert kernel.state.produced == 24
    assert sum(a.food for a in kernel.state.agents) == 42 - kernel.state.consumed
    assert sum(a.unmet for a in kernel.state.agents) == 48 - kernel.state.consumed >= 6


@pytest.mark.parametrize("issue", ["obstacle", "unknown_workplace", "duplicate_id", "duplicate_tile",
                                   "empty_schedule", "unreachable", "capacity", "jagged"])
def test_bad_scenario_fails_before_start(scenario_data, issue):
    if issue == "obstacle":
        scenario_data["profiles"][0]["position"] = [2, 2]
    elif issue == "unknown_workplace":
        scenario_data["profiles"][0]["workplace"] = "missing"
    elif issue == "duplicate_id":
        scenario_data["profiles"][1]["id"] = "A1"
    elif issue == "duplicate_tile":
        scenario_data["zones"][1]["tiles"] = [[1, 1]]
    elif issue == "empty_schedule":
        scenario_data["harvest"] = []
    elif issue == "unreachable":
        scenario_data["grid"][3] = "############"
    elif issue == "capacity":
        scenario_data["zones"][0]["capacity"] = 1
    else:
        scenario_data["grid"][0] = "."
    with pytest.raises(ValidationError):
        TownScenario.model_validate_json(json.dumps(scenario_data))


def test_moves(town):
    kernel = active(town)
    event = kernel.submit(kernel.turn, {"type": "MOVE", "x": 2, "y": 1})
    assert event.position == kernel.state.agent("A1").position == (2, 1)
    advance(kernel, "A1", 2)
    rejected(kernel, {"type": "MOVE", "x": 2, "y": 2}, "blocked_tile")


@pytest.mark.parametrize("target", [(8, 1), (2, 2), (1, 1)])
def test_non_adjacent_moves(town, target):
    rejected(active(town), {"type": "MOVE", "x": target[0], "y": target[1]}, "not_adjacent")


def test_map_edge_and_full_zone(scenario_data):
    scenario_data["profiles"][0]["position"] = [0, 1]
    scenario_data["zones"][0]["capacity"] = 1
    kernel = active(TownScenario.model_validate_json(json.dumps(scenario_data)))
    rejected(kernel, {"type": "MOVE", "x": -1, "y": 1}, "blocked_tile")
    advance(kernel, "A1", 2)
    rejected(kernel, {"type": "MOVE", "x": 1, "y": 1}, "zone_full")


def test_work_and_gifts(town):
    kernel = active(town)
    wage = kernel.submit(kernel.turn, {"type": "WORK", "workplace": "farm"})
    assert wage.entries == (Entry("coins", "@treasury", "A1", 2),)
    assert kernel.state.treasury == 58 and kernel.state.agent("A1").coins == 22
    gift = kernel.submit(kernel.turn, {"type": "GIVE_FOOD", "recipient_id": "A1", "quantity": 2})
    assert gift.entries == (Entry("food", "A2", "A1", 2),)
    assert [a.food for a in kernel.state.agents[:2]] == [15, 5]
    rejected(kernel, {"type": "GIVE_FOOD", "recipient_id": "A1", "quantity": 1}, "wrong_location")


@pytest.mark.parametrize(("payload", "reason"), [
    ({"type": "WORK", "workplace": "clinic"}, "ineligible_workplace"),
    ({"type": "GIVE_FOOD", "recipient_id": "A1", "quantity": 1}, "self_transfer"),
    ({"type": "GIVE_FOOD", "recipient_id": "unknown", "quantity": 1}, "unknown_recipient"),
    ({"type": "GIVE_FOOD", "recipient_id": "A2", "quantity": 14}, "insufficient_food"),
    ({"type": "WAIT", "actor": "A2"}, "invalid_schema"),
    ({"type": "MINT"}, "invalid_schema"),
    ({"type": "ACCEPT_OFFER", "offer_id": "missing"}, "unknown_offer"),
])
def test_rejected_turn(town, payload, reason):
    rejected(active(town), payload, reason)


def test_workplace_and_treasury(scenario_data):
    scenario_data["treasury"] = 1
    kernel = active(TownScenario.model_validate_json(json.dumps(scenario_data)))
    rejected(kernel, {"type": "WORK", "workplace": "farm"}, "insufficient_treasury")
    rejected(kernel, {"type": "WORK", "workplace": "market"}, "wrong_location")


@pytest.mark.parametrize("field", ["quantity", "price"])
@pytest.mark.parametrize("value", [0, -1, 10**30, True, 1.5, "1"])
def test_invalid_offer_numbers(town, field, value):
    rejected(active(town), {"type": "CREATE_OFFER", "recipient_id": "A2", "quantity": 1,
                            "price": 1, "expiry_round": 1, field: value}, "invalid_schema")


@pytest.mark.parametrize(("changes", "reason"), [
    ({"recipient_id": "A1"}, "self_transfer"), ({"expiry_round": 0}, "invalid_expiry"),
    ({"expiry_round": 9}, "invalid_expiry"), ({"quantity": 14}, "insufficient_food"),
])
def test_invalid_offer_terms(town, changes, reason):
    rejected(active(town), {"type": "CREATE_OFFER", "recipient_id": "A2", "quantity": 1,
                            "price": 1, "expiry_round": 1, **changes}, reason)


def test_trade_is_atomic_and_once_only(town):
    kernel = active(town)
    agents = kernel.state.agents
    listing = offer(kernel, expiry_round=1)
    assert kernel.state.agents == (replace(agents[0], last_action="CREATE_OFFER"), *agents[1:])
    turn = kernel.turn

    def attempt():
        try:
            return kernel.submit(turn, accept(listing.id)).kind
        except TurnConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        assert sorted(f.result() for f in futures) == ["ACCEPT_OFFER", "conflict"]
    assert kernel.events[-1].entries == (Entry("food", "A1", "A2", 3), Entry("coins", "A2", "A1", 5))
    assert [(a.food, a.coins) for a in kernel.state.agents[:2]] == [(10, 25), (10, 30)]
    assert kernel.state.offers[0].status == "accepted"
    advance(kernel, "A2", 2)
    rejected(kernel, accept(listing.id), "offer_closed")


def test_insufficient_coins_and_wrong_buyer(town):
    kernel = active(town)
    listing = offer(kernel, price=36)
    rejected(kernel, accept(listing.id), "insufficient_coins")
    rejected(kernel, accept(listing.id), "wrong_buyer")


def test_insufficient_food_after_posting(scenario_data):
    scenario_data["harvest"] = [0, 0]
    kernel = active(TownScenario.model_validate_json(json.dumps(scenario_data)))
    listing = offer(kernel, quantity=7)
    advance(kernel, "A2", 2)
    rejected(kernel, accept(listing.id), "insufficient_food")


def test_expiry_and_remote_acceptance(town):
    kernel = active(town)
    listing = offer(kernel, recipient_id="A3", expiry_round=1)
    advance(kernel, "A3", 1)
    rejected(kernel, accept(listing.id), "wrong_location")
    advance(kernel, "A3", 2)
    assert kernel.state.offers[0].status == "expired"
    rejected(kernel, accept(listing.id), "offer_closed")


def test_owner_revocation(town):
    kernel = active(town)
    listing = offer(kernel, expiry_round=3)
    revoke = {"type": "REVOKE_OFFER", "offer_id": listing.id}
    rejected(kernel, revoke, "wrong_seller")
    advance(kernel, "A1", 2)
    assert kernel.submit(kernel.turn, revoke).offers[0].status == "revoked"
    advance(kernel, "A2", 3)
    rejected(kernel, accept(listing.id), "offer_closed")


def test_mismatched_and_stale_turns(town):
    kernel = active(town)
    turn = kernel.turn
    for conflict in [replace(turn, actor="A2"), replace(turn, run_id="other"), replace(turn, round=99)]:
        before = kernel.state
        with pytest.raises(TurnConflict):
            kernel.submit(conflict, WAIT)
        assert kernel.state is before
    event = kernel.submit(turn, WAIT)
    before = kernel.state
    with pytest.raises(TurnConflict):
        kernel.submit(turn, WAIT)
    with pytest.raises(ValueError, match="out-of-order"):
        reduce_event(before, event)
    assert kernel.state is before
