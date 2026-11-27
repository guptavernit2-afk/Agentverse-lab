from dataclasses import replace

from agentverse.domain.actions import AcceptOffer, CreateOffer, GiveFood, Move, Proposal, RevokeOffer, Wait, Work
from agentverse.domain.model import TREASURY, Entry, Event, Offer, World


class Rejection(ValueError):
    """Stable reason code for an invalid proposal on the current turn."""


def resolve(world: World, actor_id: str, action: Proposal) -> Event:
    actor = world.agent(actor_id)
    event = Event(world.version + 1, world.round, action.type, actor_id)
    scenario = world.scenario

    if isinstance(action, Wait):
        return event
    if isinstance(action, Move):
        target = (action.x, action.y)
        x, y = actor.position
        if abs(action.x - x) + abs(action.y - y) != 1:
            raise Rejection("not_adjacent")
        if not scenario.walkable(target):
            raise Rejection("blocked_tile")
        for zone in scenario.zones:
            if target in zone.tiles and actor.position not in zone.tiles:
                if sum(a.position in zone.tiles for a in world.agents) >= zone.capacity:
                    raise Rejection("zone_full")
        return replace(event, position=target)
    if isinstance(action, Work):
        profile = next(p for p in scenario.profiles if p.id == actor_id)
        if profile.workplace != action.workplace:
            raise Rejection("ineligible_workplace")
        zone = next(z for z in scenario.zones if z.id == action.workplace)
        if actor.position not in zone.tiles:
            raise Rejection("wrong_location")
        if world.treasury < 2:
            raise Rejection("insufficient_treasury")
        return replace(event, entries=(Entry("coins", TREASURY, actor_id, 2),))
    if isinstance(action, (GiveFood, CreateOffer)):
        if action.recipient_id == actor_id:
            raise Rejection("self_transfer")
        if action.recipient_id not in {a.id for a in world.agents}:
            raise Rejection("unknown_recipient")
        if actor.food < action.quantity:
            raise Rejection("insufficient_food")
        if isinstance(action, GiveFood):
            if actor.position != world.agent(action.recipient_id).position:
                raise Rejection("wrong_location")
            return replace(event, entries=(Entry("food", actor_id, action.recipient_id, action.quantity),))
        if not world.round <= action.expiry_round <= len(scenario.harvest):
            raise Rejection("invalid_expiry")
        offer = Offer(f"offer-{event.sequence}", actor_id, action.recipient_id,
                      action.quantity, action.price, action.expiry_round)
        return replace(event, offers=(offer,))

    offer = next((o for o in world.offers if o.id == action.offer_id), None)
    if offer is None:
        raise Rejection("unknown_offer")
    if offer.status != "open" or offer.expiry_round < world.round:
        raise Rejection("offer_closed")
    if isinstance(action, RevokeOffer):
        if actor_id != offer.seller:
            raise Rejection("wrong_seller")
        return replace(event, offers=(replace(offer, status="revoked"),))
    if not isinstance(action, AcceptOffer):
        raise TypeError("unsupported action")
    if actor_id != offer.buyer:
        raise Rejection("wrong_buyer")
    seller = world.agent(offer.seller)
    if seller.position != actor.position:
        raise Rejection("wrong_location")
    if seller.food < offer.quantity:
        raise Rejection("insufficient_food")
    if actor.coins < offer.price:
        raise Rejection("insufficient_coins")
    return replace(event, entries=(Entry("food", seller.id, actor_id, offer.quantity),
                                   Entry("coins", actor_id, seller.id, offer.price)),
                   offers=(replace(offer, status="accepted"),))
