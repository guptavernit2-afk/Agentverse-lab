from dataclasses import replace

from agentverse.domain.actions import CreateCommitment, FulfillCommitment, NoteInput, Speak
from agentverse.domain.model import Entry, Event, World
from agentverse.domain.social import BOARD, Belief, Commitment, DecisionNote, Message
from .economy import Rejection


def same_zone(world: World, first: str, second: str) -> bool:
    left = world.agent(first).position
    right = world.agent(second).position
    return any(left in zone.tiles and right in zone.tiles for zone in world.scenario.zones)


def check_references(world: World, actor: str, claims: list[str], evidence: list[str]) -> None:
    if set(claims) - {claim.id for claim in world.social.claims}:
        raise Rejection("unknown_claim")
    if set(evidence) - {record.id for record in world.social.visible_evidence(actor)}:
        raise Rejection("unavailable_evidence")


def decision_note(world: World, actor: str, raw: object) -> DecisionNote:
    if not isinstance(raw, dict):
        raise Rejection("invalid_schema")
    note = NoteInput.model_validate(raw)
    check_references(world, actor, [b.claim_id for b in note.beliefs], note.evidence_ids)
    return DecisionNote(actor, world.round, note.summary, tuple(note.evidence_ids),
                        tuple(Belief(b.claim_id, b.interpretation) for b in note.beliefs))


def check_recipient(world: World, actor: str, recipient: str) -> None:
    if recipient == actor or recipient not in {a.id for a in world.agents}:
        raise Rejection("invalid_recipient")
    if not same_zone(world, actor, recipient):
        raise Rejection("outside_communication_zone")


def resolve_social(world: World, actor: str, action: Speak | CreateCommitment | FulfillCommitment) -> Event:
    event = Event(world.version + 1, world.round, action.type, actor)
    slot = f"{world.round}-{world.cursor + 1}"
    if isinstance(action, Speak):
        if action.recipient_id != BOARD:
            check_recipient(world, actor, action.recipient_id)
        check_references(world, actor, action.claim_ids, action.evidence_ids)
        message = Message(f"message-{slot}", actor, action.recipient_id, action.text, world.round,
                          tuple(action.claim_ids), tuple(action.evidence_ids))
        return replace(event, message=message)

    if isinstance(action, CreateCommitment):
        check_recipient(world, actor, action.beneficiary_id)
        if not world.round <= action.due_round <= len(world.scenario.harvest):
            raise Rejection("invalid_due_round")
        promise = Commitment(f"commitment-{slot}", actor, action.beneficiary_id, action.quantity, 0,
                             world.round, action.due_round, "OPEN", (event.sequence,))
        return replace(event, commitments=(promise,))

    promise = next((c for c in world.social.commitments if c.id == action.commitment_id
                    and actor in (c.promisor, c.beneficiary)), None)
    if promise is None:
        raise Rejection("unavailable_commitment")
    if promise.promisor != actor:
        raise Rejection("wrong_promisor")
    if not promise.outstanding or world.round > promise.due_round:
        raise Rejection("commitment_closed")
    if world.agent(actor).position != world.agent(promise.beneficiary).position:
        raise Rejection("wrong_location")
    delivered = promise.delivered + action.quantity
    if delivered > promise.quantity:
        raise Rejection("overdelivery")
    if world.agent(actor).food < action.quantity:
        raise Rejection("insufficient_food")
    updated = replace(promise, delivered=delivered, events=(*promise.events, event.sequence),
                      status="FULFILLED" if delivered == promise.quantity else "PARTIAL")
    transfer = Entry("food", actor, promise.beneficiary, action.quantity)
    return replace(event, entries=(transfer,), commitments=(updated,))
