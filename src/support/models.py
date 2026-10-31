from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Context(Strict):
    tenant_id: str
    actor_id: str
    role: Literal["owner", "viewer"]
    request_id: str


class Resync(Strict):
    venue_id: str = Field(min_length=1, max_length=120)


class Cancel(Strict):
    business_id: str
    subscription_id: str
    retained_subscription_id: str


class Refund(Strict):
    business_id: str
    payment_id: str
    related_payment_id: str


class Promo(Strict):
    venue_id: str
    discount_percent: int = Field(strict=True, ge=1, le=100)
    starts_at: datetime
    expires_at: datetime
    max_redemptions: int = Field(strict=True, ge=1)

    @model_validator(mode="after")
    def dates(self):
        if not self.starts_at.tzinfo or not self.expires_at.tzinfo or self.expires_at <= self.starts_at:
            raise ValueError("Timezone-aware dates and expiry after start are required")
        return self


class ResyncProposal(Strict):
    type: Literal["resync_pos"]
    parameters: Resync


class CancelProposal(Strict):
    type: Literal["cancel_duplicate_subscription"]
    parameters: Cancel


class PromoProposal(Strict):
    type: Literal["create_promo"]
    parameters: Promo


class RefundProposal(Strict):
    type: Literal["create_refund_request"]
    parameters: Refund


Proposal = Annotated[ResyncProposal | CancelProposal | PromoProposal | RefundProposal, Field(discriminator="type")]


class Evidence(Strict):
    kind: Literal["log", "kb"]
    id: str
    summary: str = Field(max_length=2000)


class Question(Strict):
    field: str
    prompt: str
    options: list[str] | None = None


class AgentResponse(Strict):
    """Agent proposes; only the support API can create executable previews."""
    reply: str = Field(min_length=1, max_length=16000)
    state: Literal["needs_input", "unresolved", "resolved", "investigating"]
    questions: list[Question] = Field(default_factory=list, max_length=10)
    evidence: list[Evidence] = Field(default_factory=list, max_length=30)
    proposal: Proposal | None = None


class Prepared(Strict):
    summary: str
    preconditions: dict
    preview: dict = Field(default_factory=dict)
    evidence_ids: list[str]


class Execution(Strict):
    type: Literal["resync_pos", "cancel_duplicate_subscription", "create_promo", "create_refund_request"]
    resource_id: str
    before: dict | None
    after: dict
    verification: dict


class MessageInput(Strict):
    client_message_id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=8000)


class Decision(Strict):
    decision: Literal["confirm", "reject"]


class Login(Strict):
    token: str = Field(min_length=1, max_length=500)
