"""Immutable social records. Event sequence links are for operator audit."""

from dataclasses import dataclass
from typing import Literal

BOARD = "board"


@dataclass(frozen=True)
class Claim:
    id: str
    key: Literal["reduced_harvest"]
    source: str
    text: str


@dataclass(frozen=True)
class Evidence:
    id: str
    claim_id: str
    issuer_id: str
    source_event_id: str
    issued_round: int
    kind: Literal["harvest_record"]
    status: Literal["supported", "contradicted"]
    payload: tuple[int, ...]
    visibility_policy: Literal["explicit_grants"] = "explicit_grants"


@dataclass(frozen=True)
class Grant:
    evidence_id: str
    # None denotes a public grant.
    grantee: str | None


@dataclass(frozen=True)
class Message:
    id: str
    sender: str
    recipient: str
    text: str
    round: int
    claim_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class Belief:
    claim_id: str
    interpretation: str


@dataclass(frozen=True)
class DecisionNote:
    author: str
    round: int
    summary: str
    evidence_ids: tuple[str, ...]
    beliefs: tuple[Belief, ...]


@dataclass(frozen=True)
class Commitment:
    id: str
    promisor: str
    beneficiary: str
    quantity: int
    delivered: int
    created_round: int
    due_round: int
    status: Literal["OPEN", "PARTIAL", "FULFILLED", "BROKEN"]
    events: tuple[int, ...]

    @property
    def outstanding(self) -> bool:
        return self.status in ("OPEN", "PARTIAL")


@dataclass(frozen=True)
class TrustEdge:
    observer: str
    subject: str
    score: int = 50


@dataclass(frozen=True)
class SocialState:
    trust: tuple[TrustEdge, ...] = ()
    claims: tuple[Claim, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    grants: tuple[Grant, ...] = ()
    messages: tuple[Message, ...] = ()
    commitments: tuple[Commitment, ...] = ()
    notes: tuple[DecisionNote, ...] = ()

    def visible_evidence(self, actor: str) -> tuple[Evidence, ...]:
        allowed = {g.evidence_id for g in self.grants if g.grantee in (None, actor)}
        return tuple(e for e in self.evidence if e.id in allowed)
