from dataclasses import replace

from .model import Entry, Event
from .social import SocialState


def apply_social(state: SocialState, event: Event) -> SocialState:
    if event.claim:
        state = replace(state, claims=(*state.claims, event.claim))
    if event.evidence:
        state = replace(state, evidence=(*state.evidence, event.evidence))
    if event.grant:
        state = replace(state, grants=(*state.grants, event.grant))
    if event.message:
        state = replace(state, messages=(*state.messages, event.message))
    if event.note:
        state = replace(state, notes=(*state.notes, event.note))
    if event.kind in ("CREATE_COMMITMENT", "FULFILL_COMMITMENT") and len(event.commitments) != 1:
        raise ValueError("a commitment action must update exactly one promise")
    if event.kind == "ROUND_SETTLED":
        due = {c.id for c in state.commitments if c.outstanding and c.due_round == event.round}
        if {c.id for c in event.commitments} != due:
            raise ValueError("settlement must resolve all due commitments")
    if not event.commitments:
        return state

    promises = {c.id: c for c in state.commitments}
    trust = {(e.observer, e.subject): e for e in state.trust}
    for change in event.commitments:
        previous = promises.get(change.id)
        if previous is None:
            if (event.kind != "CREATE_COMMITMENT" or change.status != "OPEN" or change.delivered != 0
                    or change.events != (event.sequence,) or change.created_round != event.round
                    or change.promisor != event.actor or change.quantity <= 0 or event.entries):
                raise ValueError("invalid commitment creation")
        else:
            if not previous.outstanding or change.events != (*previous.events, event.sequence):
                raise ValueError("invalid commitment transition")
            expected = replace(previous, delivered=change.delivered, status=change.status, events=change.events)
            if change != expected:
                raise ValueError("commitment terms are immutable")
            if event.kind == "FULFILL_COMMITMENT":
                amount = change.delivered - previous.delivered
                expected = Entry("food", previous.promisor, previous.beneficiary, amount)
                status = "FULFILLED" if change.delivered == previous.quantity else "PARTIAL"
                if (event.actor != previous.promisor or event.round > previous.due_round
                        or amount <= 0 or change.delivered > previous.quantity or change.status != status
                        or event.entries != (expected,)):
                    raise ValueError("commitment delivery must match its inventory transfer")
            elif (event.kind != "ROUND_SETTLED" or previous.due_round != event.round
                  or change.status != "BROKEN" or change.delivered != previous.delivered):
                raise ValueError("invalid commitment settlement")
            if not change.outstanding:
                key = previous.beneficiary, previous.promisor
                edge = trust[key]
                delta = 8 if change.status == "FULFILLED" else -12
                trust[key] = replace(edge, score=max(0, min(100, edge.score + delta)))
        promises[change.id] = change
    return replace(state, commitments=tuple(promises.values()), trust=tuple(trust.values()))
