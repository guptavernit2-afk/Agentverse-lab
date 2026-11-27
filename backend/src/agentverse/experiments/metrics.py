from collections import Counter
from dataclasses import asdict
from statistics import mean

from agentverse.domain.model import Event, World
from agentverse.simulation.kernel import Kernel


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def gini(values: list[int]) -> float | None:
    if any(x < 0 for x in values):
        raise ValueError("negative inventory")
    n = len(values)
    return ratio(sum((2 * i - n - 1) * x for i, x in enumerate(sorted(values), 1)), n * sum(values))


def measure(world: World, events: tuple[Event, ...]) -> dict:
    turns = [e for e in events if e.actor is not None]
    failures = sum((e.reason or "").startswith("provider_") for e in turns)
    rejected = sum(e.reason is not None for e in turns) - failures
    statuses = Counter(c.status for c in world.social.commitments)
    stock = [a.food for a in world.agents]

    def volume(kind):
        return sum(entry.amount for e in turns if e.kind == kind for entry in e.entries if entry.asset == "food")

    return {
        "round": world.round, "unmet_units": sum(a.unmet for a in world.agents),
        "agents_affected": sum(a.unmet > 0 for a in world.agents), "food_units": sum(stock),
        "produced_units": world.produced, "consumed_units": world.consumed,
        "agent_coins": sum(a.coins for a in world.agents), "treasury_coins": world.treasury,
        "holdings": {a.id: {"food": a.food, "coins": a.coins, "unmet": a.unmet} for a in world.agents},
        "trades": sum(e.kind == "ACCEPT_OFFER" for e in turns), "trade_units": volume("ACCEPT_OFFER"),
        "gift_units": volume("GIVE_FOOD"), "fulfillment_units": volume("FULFILL_COMMITMENT"),
        "commitments_created": len(world.social.commitments),
        **{name.lower(): statuses[name] for name in ("OPEN", "PARTIAL", "FULFILLED", "BROKEN")},
        "fulfillment_rate": ratio(statuses["FULFILLED"], statuses["FULFILLED"] + statuses["BROKEN"]),
        "mean_trust": mean(e.score for e in world.social.trust),
        "trust_edges": [asdict(e) for e in world.social.trust], "food_gini": gini(stock),
        "evidence_citations": sum(bool(e.note and e.note.evidence_ids) for e in turns),
        "scheduled_turns": len(turns), "proposals": len(turns) - failures, "rejected": rejected,
        "provider_failures": failures, "invalid_rate": ratio(rejected, len(turns) - failures),
    }


def trajectory(kernel: Kernel) -> list[dict]:
    events = kernel.events
    return [measure(kernel.world_at(e.sequence), events[:e.sequence]) for e in events if e.kind == "ROUND_SETTLED"]


def differences(control: dict, treatment: dict) -> dict:
    return {key: (treatment[key] - value if value is not None and treatment[key] is not None else None)
            for key, value in control.items() if key != "round" and (type(value) in (int, float) or value is None)}
