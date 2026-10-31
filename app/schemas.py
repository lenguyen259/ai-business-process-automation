from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class ProcessType(str, Enum):
    PURCHASE_APPROVAL = "purchase_approval"
    CUSTOMER_ONBOARDING = "customer_onboarding"
    INCIDENT_TRIAGE = "incident_triage"


class ProcessStatus(str, Enum):
    DRAFT = "draft"
    AI_REVIEW = "ai_review"
    PENDING_APPROVAL = "pending_approval"
    INTEGRATING = "integrating"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class ProcessCreateRequest(BaseModel):
    process_type: ProcessType
    payload: dict[str, Any] = Field(default_factory=dict)


class ProcessDecisionRequest(BaseModel):
    approve: bool
    note: str | None = None


class ProcessResponse(BaseModel):
    id: int
    process_type: ProcessType
    status: ProcessStatus
    requester: str
    payload: dict[str, Any]
    ai_recommendation: str | None = None
    ai_rationale: str | None = None
    external_refs: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str
