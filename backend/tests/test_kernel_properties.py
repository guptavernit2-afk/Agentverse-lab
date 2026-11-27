from collections import Counter
from dataclasses import replace

from hypothesis import event as classify, given, settings, strategies as st

from agentverse.domain.model import TREASURY
from agentverse.simulation.kernel import Kernel


def check_transaction(before, event, after):
    """Independent per-account reconciliation of both sides of every entry."""
    balances = {(a.id, asset): getattr(a, asset) for a in before.agents for asset in ("food", "coins")}
    balances[TREASURY, "coins"] = before.treasury
    for entry in event.entries:
        assert type(entry.amount) is int and entry.amount > 0
        if entry.source is not None:
            balances[entry.source, entry.asset] -= entry.amount
        if entry.destination is not None:
            balances[entry.destination, entry.asset] += entry.amount
    for agent in after.agents:
        assert agent.food == balances[agent.id, "food"] >= 0
        assert agent.coins == balances[agent.id, "coins"] >= 0
        assert after.scenario.walkable(agent.position)
    assert after.treasury == balances[TREASURY, "coins"] >= 0
    assert after.treasury + sum(a.coins for a in after.agents) == 210
    assert after.version == event.sequence == before.version + 1
    if event.reason:
        assert event.kind == "WAIT"
        expected = tuple(replace(a, last_action="WAIT", last_rejection=event.reason)
                         if a.id == event.actor else a for a in before.agents)
        assert after == replace(before, agents=expected, version=after.version,
                                cursor=before.cursor + 1, stage=after.stage)


def proposal(kernel, kind, number):
    w, actor = kernel.state, kernel.turn.actor
    recipient = w.agents[number % 6].id
    if kind == "GIVE_FOOD":
        return {"type": kind, "recipient_id": recipient, "quantity": number}
    if kind == "CREATE_OFFER":
        return {"type": kind, "recipient_id": recipient, "quantity": 1 + number % 3,
                "price": number, "expiry_round": w.round + number % 3}
    if kind in ("ACCEPT_OFFER", "REVOKE_OFFER"):
        offer_id = w.offers[number % len(w.offers)].id if w.offers else "missing"
        return {"type": kind, "offer_id": offer_id}
    if kind == "MOVE":
        x, y = w.agent(actor).position
        dx, dy = ((-1, 0), (1, 0), (0, 1), (0, -1), (2, 2))[number % 5]
        return {"type": kind, "x": x + dx, "y": y + dy}
    if kind == "WORK":
        workplace = next(p.workplace for p in w.scenario.profiles if p.id == actor)
        return {"type": kind, "workplace": workplace}
    return {"type": kind}


KINDS = ["GIVE_FOOD", "CREATE_OFFER", "ACCEPT_OFFER", "REVOKE_OFFER", "MOVE", "WORK", "WAIT", "UNKNOWN"]


@settings(max_examples=150, deadline=None, derandomize=True, print_blob=True)
@given(seed=st.integers(-10000, 10000),
       steps=st.lists(st.tuples(st.sampled_from(KINDS), st.integers(-2, 12)), min_size=8, max_size=36))
def test_seeded_action_sequences(town, seed, steps):
    kernel = Kernel(town, seed, run_id="property")
    actions = [("WAIT", 0), ("UNKNOWN", 0), *steps]
    supply = 18
    outcomes = Counter()
    for kind, number in actions:
        if kernel.state.stage == "ready":
            before = kernel.state
            start = kernel.start_round()
            check_transaction(before, start, kernel.state)
            supply += town.harvest[start.round - 1]
        before = kernel.state
        actor = kernel.turn.actor
        result = kernel.submit(kernel.turn, proposal(kernel, kind, number))
        assert result.actor == actor
        outcomes["rejected" if result.reason else "accepted"] += 1
        check_transaction(before, result, kernel.state)
        assert sum(a.food for a in kernel.state.agents) == supply
        if kernel.state.stage == "settlement":
            before = kernel.state
            meals = sum(a.food > 0 for a in before.agents)
            settle = kernel.settle_round()
            check_transaction(before, settle, kernel.state)
            supply -= meals
            assert sum(a.food for a in kernel.state.agents) == supply
            assert set(settle.hungry) == {a.id for a in before.agents if a.food == 0}
    assert outcomes["accepted"] and outcomes["rejected"]
    classify("mixed accepted and rejected turns")
