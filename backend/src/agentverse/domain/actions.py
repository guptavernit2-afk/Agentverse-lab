"""Only the action payload crosses the untrusted proposal boundary."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter

from agentverse.experiments.town import Name

# Fixed protocol limit for unit quantities and total prices.
Amount = Annotated[int, Field(gt=0, le=1_000_000)]


class Action(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class Wait(Action):
    type: Literal["WAIT"]


class Move(Action):
    type: Literal["MOVE"]
    x: int
    y: int


class Work(Action):
    type: Literal["WORK"]
    workplace: Name


class GiveFood(Action):
    type: Literal["GIVE_FOOD"]
    recipient_id: Name
    quantity: Amount


class CreateOffer(Action):
    type: Literal["CREATE_OFFER"]
    recipient_id: Name
    quantity: Amount
    price: Amount
    expiry_round: int


class AcceptOffer(Action):
    type: Literal["ACCEPT_OFFER"]
    offer_id: Name


class RevokeOffer(Action):
    type: Literal["REVOKE_OFFER"]
    offer_id: Name


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]
References = Annotated[list[Name], Field(max_length=8)]


class Speak(Action):
    type: Literal["SPEAK"]
    recipient_id: Name
    text: ShortText
    claim_ids: References = Field(default_factory=list)
    evidence_ids: References = Field(default_factory=list)


class CreateCommitment(Action):
    type: Literal["CREATE_COMMITMENT"]
    beneficiary_id: Name
    quantity: Amount
    due_round: int


class FulfillCommitment(Action):
    type: Literal["FULFILL_COMMITMENT"]
    commitment_id: Name
    quantity: Amount


class ReportedBelief(Action):
    claim_id: Name
    interpretation: ShortText


class NoteInput(Action):
    summary: ShortText
    evidence_ids: References = Field(default_factory=list)
    beliefs: Annotated[list[ReportedBelief], Field(max_length=8)] = Field(default_factory=list)


Proposal = Wait | Move | Work | GiveFood | CreateOffer | AcceptOffer | RevokeOffer | Speak | CreateCommitment | FulfillCommitment
proposal_schema = TypeAdapter(Annotated[Proposal, Field(discriminator="type")])
