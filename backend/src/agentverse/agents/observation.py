"""Allowlisted agent context. Only this serialized value crosses the policy boundary."""

from collections import deque
from dataclasses import dataclass
import json
from typing import Iterable

from agentverse.domain.model import Event, World
from agentverse.domain.social import BOARD, Commitment, Message

MEMORY_LIMIT = 12
ACTIONS = ("WAIT", "MOVE", "WORK", "GIVE_FOOD", "CREATE_OFFER", "ACCEPT_OFFER",
           "REVOKE_OFFER", "SPEAK", "CREATE_COMMITMENT", "FULFILL_COMMITMENT")


@dataclass(frozen=True)
class Observation:
    policy_context: str

    def as_dict(self) -> dict:
        return json.loads(self.policy_context)


def promise_view(c: Commitment) -> dict:
    return {"id": c.id, "promisor": c.promisor, "beneficiary": c.beneficiary,
            "quantity": c.quantity, "delivered": c.delivered, "created_round": c.created_round,
            "due_round": c.due_round, "status": c.status}


def message_view(message: Message, world: World, actor: str) -> dict:
    authorized = {e.id for e in world.social.visible_evidence(actor)}
    return {"id": message.id, "sender": message.sender, "recipient": message.recipient,
            "text": message.text, "round": message.round, "claim_ids": message.claim_ids,
            "evidence_ids": [key for key in message.evidence_ids if key in authorized]}


def visible_reason(reason: str | None) -> str | None:
    # A guessed private offer ID and an unknown one must produce identical agent feedback.
    if reason in ("wrong_buyer", "wrong_seller", "unknown_offer", "offer_closed"):
        return "unavailable_offer"
    return reason


def visible_record(event: Event, world: World, actor: str) -> dict | None:
    details = {}
    if event.actor == actor:
        details["action"] = event.kind
        details["reason"] = visible_reason(event.reason)
        if event.position is not None:
            details["position"] = event.position
    if event.claim:
        details["claim_id"] = event.claim.id
    if event.grant and event.grant.grantee in (None, actor):
        details["evidence_id"] = event.grant.evidence_id
    if event.message and (event.message.recipient in (BOARD, actor) or event.message.sender == actor):
        details["message"] = message_view(event.message, world, actor)
    if event.note and event.note.author == actor:
        details["self_report"] = {
            "summary": event.note.summary, "evidence_ids": event.note.evidence_ids,
            "beliefs": [{"claim_id": b.claim_id, "interpretation": b.interpretation} for b in event.note.beliefs],
        }
    transfers = [{"asset": entry.asset, "source": entry.source, "destination": entry.destination,
                  "amount": entry.amount} for entry in event.entries if actor in (entry.source, entry.destination)]
    if transfers:
        details["transfers"] = transfers
    if event.kind == "ROUND_SETTLED":
        details["unmet_food"] = actor in event.hungry
    personal = [promise_view(c) for c in event.commitments if actor in (c.promisor, c.beneficiary)]
    if personal:
        details["commitments"] = personal
    offers = [offer.id for offer in event.offers if actor in (offer.seller, offer.buyer)]
    if offers:
        details["offer_ids"] = offers
    return {"round": event.round, **details} if details else None


def project(world: World, actor_id: str, history: Iterable[tuple[Event, World]]) -> Observation:
    own = world.agent(actor_id)
    config = world.scenario
    profile = next(p for p in config.profiles if p.id == actor_id)
    zone = next((z for z in config.zones if own.position in z.tiles), None)
    nearby_tiles = set(zone.tiles) if zone else {own.position}
    records = deque([{"id": "seen-0", "round": 0, "seed_memory": profile.seed_memory}], maxlen=MEMORY_LIMIT)
    seen = 0
    for event, at_event in history:
        record = visible_record(event, at_event, actor_id)
        if record is not None:
            seen += 1
            records.append({"id": f"seen-{seen}", **record})

    social = world.social
    evidence = social.visible_evidence(actor_id)
    statuses = {e.claim_id: e.status for e in evidence}
    messages = [m for m in social.messages if m.sender == actor_id or m.recipient in (actor_id, BOARD)]
    context = {
        "round": world.round,
        "self": {"id": own.id, "role": profile.role, "goal": profile.goal, "workplace": profile.workplace,
                 "position": own.position, "food": own.food, "coins": own.coins, "unmet": own.unmet,
                 "last_unmet": own.last_unmet, "last_action": own.last_action,
                 "last_rejection": visible_reason(own.last_rejection)},
        "map": {"grid": config.grid, "zones": [{"id": z.id, "tiles": z.tiles, "capacity": z.capacity}
                                               for z in config.zones]},
        "nearby": [{"id": a.id, "position": a.position} for a in world.agents
                   if a.id != actor_id and a.position in nearby_tiles],
        "claims": [{"id": c.id, "key": c.key, "source": c.source, "text": c.text,
                    "status": statuses.get(c.id, "unverified")} for c in social.claims],
        "evidence": [{"id": e.id, "claim_id": e.claim_id, "issuer": e.issuer_id,
                      "source_event_id": e.source_event_id, "issued_round": e.issued_round,
                      "kind": e.kind, "status": e.status, "payload": e.payload} for e in evidence],
        "messages": [message_view(m, world, actor_id) for m in messages[-MEMORY_LIMIT:]],
        "offers": [{"id": o.id, "seller": o.seller, "buyer": o.buyer, "quantity": o.quantity,
                    "price": o.price, "expiry_round": o.expiry_round}
                   for o in world.offers if o.status == "open" and actor_id in (o.buyer, o.seller)],
        "obligations": [promise_view(c) for c in social.commitments
                        if c.outstanding and actor_id in (c.promisor, c.beneficiary)],
        "trust": {e.subject: e.score for e in social.trust if e.observer == actor_id},
        "memory": list(records),
        "allowed_actions": ACTIONS,
    }
    return Observation(json.dumps(context, sort_keys=True, separators=(",", ":"), allow_nan=False))
