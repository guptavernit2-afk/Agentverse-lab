"""Apply one validated atomic transaction, then reconcile its resulting world."""

from dataclasses import replace

from .model import TREASURY, Event, World


def check_invariants(world: World) -> None:
    config = world.scenario
    if any(a.food < 0 or a.coins < 0 or not config.walkable(a.position) for a in world.agents):
        raise ValueError("negative balance or illegal position")
    if world.treasury < 0 or sum(a.coins for a in world.agents) + world.treasury != (
        config.treasury + sum(p.coins for p in config.profiles)
    ):
        raise ValueError("coin conservation failed")
    if sum(a.food for a in world.agents) != (
        sum(p.food for p in config.profiles) + world.produced - world.consumed
    ):
        raise ValueError("food conservation failed")
    for zone in config.zones:
        if sum(a.position in zone.tiles for a in world.agents) > zone.capacity:
            raise ValueError("zone capacity exceeded")


def reduce_event(world: World, event: Event) -> World:
    if event.sequence != world.version + 1:
        raise ValueError("out-of-order event")
    agents = {agent.id: agent for agent in world.agents}
    treasury = world.treasury
    produced, consumed = world.produced, world.consumed
    for entry in event.entries:
        if entry.amount <= 0 or entry.source == entry.destination:
            raise ValueError("invalid ledger entry")
        for account, delta in ((entry.source, -entry.amount), (entry.destination, entry.amount)):
            if account is None:
                if entry.asset != "food":
                    raise ValueError("only food has an external source or sink")
                if delta < 0:
                    produced -= delta
                else:
                    consumed += delta
            elif account == TREASURY:
                if entry.asset != "coins":
                    raise ValueError("treasury holds coins")
                treasury += delta
            else:
                agent = agents[account]
                balance = getattr(agent, entry.asset) + delta
                agents[account] = replace(agent, **{entry.asset: balance})

    offers = {offer.id: offer for offer in world.offers}
    offers.update((offer.id, offer) for offer in event.offers)
    cursor = world.cursor
    if event.kind == "ROUND_STARTED":
        if world.stage != "ready" or event.round != world.round + 1:
            raise ValueError("invalid round start")
        cursor, stage = 0, "acting"
    elif event.kind == "ROUND_SETTLED":
        if world.stage != "settlement" or event.round != world.round:
            raise ValueError("invalid settlement")
        for actor, agent in agents.items():
            missed = actor in event.hungry
            agents[actor] = replace(agent, last_unmet=missed, unmet=agent.unmet + int(missed))
        stage = "finished" if event.round == len(world.scenario.harvest) else "ready"
    else:
        if (world.stage != "acting" or event.round != world.round
                or event.actor != world.order()[cursor]):
            raise ValueError("event does not belong to current turn")
        actor = agents[event.actor]
        agents[event.actor] = replace(
            actor, position=event.position if event.position is not None else actor.position,
            last_action=event.kind, last_rejection=event.reason,
        )
        cursor += 1
        stage = "settlement" if cursor == len(agents) else "acting"

    result = replace(world, agents=tuple(agents.values()), treasury=treasury, offers=tuple(offers.values()),
                     round=event.round, cursor=cursor, stage=stage, version=event.sequence,
                     produced=produced, consumed=consumed)
    check_invariants(result)
    return result
