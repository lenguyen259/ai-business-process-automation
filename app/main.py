from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db, init_db
from app.governance import governance_checklist
from app.models import ProcessInstance
from app.schemas import (
    HealthResponse,
    LoginRequest,
    ProcessCreateRequest,
    ProcessDecisionRequest,
    ProcessResponse,
    TokenResponse,
)
from app.security import User, authenticate_user, create_access_token, require_permission
from app.workflow import apply_human_decision, create_process, run_ai_review, to_response_dict

settings = get_settings()
app = FastAPI(
    title="AI Business Process Automation",
    description=(
        "AI-assisted automation platform for business workflows: "
        "requirements → technical design → AI review → approval → system integration."
    ),
    version="1.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health", response_model=HealthResponse)
def health(cfg: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", app=cfg.app_name, env=cfg.app_env)


@app.get("/governance/policy")
def get_governance_policy(
    _: Annotated[User, Depends(require_permission("governance:read"))],
) -> dict[str, Any]:
    return governance_checklist()


@app.post("/auth/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    cfg: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    user = authenticate_user(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user, cfg)
    return TokenResponse(access_token=token, role=user.role.value)


@app.post("/processes", response_model=ProcessResponse, status_code=201)
def create_process_endpoint(
    body: ProcessCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    cfg: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(require_permission("process:create"))],
) -> ProcessResponse:
    instance = create_process(
        db,
        cfg,
        process_type=body.process_type,
        requester=user.email,
        payload=body.payload,
    )
    return ProcessResponse.model_validate(to_response_dict(instance))


@app.get("/processes/{process_id}", response_model=ProcessResponse)
def get_process(
    process_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("process:read"))],
) -> ProcessResponse:
    instance = db.get(ProcessInstance, process_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="Process not found")
    return ProcessResponse.model_validate(to_response_dict(instance))


@app.post("/processes/{process_id}/ai-review", response_model=ProcessResponse)
def ai_review(
    process_id: int,
    db: Annotated[Session, Depends(get_db)],
    cfg: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(require_permission("process:execute"))],
) -> ProcessResponse:
    instance = db.get(ProcessInstance, process_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="Process not found")
    updated = run_ai_review(db, cfg, instance, actor=user.email)
    return ProcessResponse.model_validate(to_response_dict(updated))


@app.post("/processes/{process_id}/decision", response_model=ProcessResponse)
def decide(
    process_id: int,
    body: ProcessDecisionRequest,
    db: Annotated[Session, Depends(get_db)],
    cfg: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(require_permission("process:execute"))],
) -> ProcessResponse:
    instance = db.get(ProcessInstance, process_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="Process not found")
    try:
        updated = apply_human_decision(
            db,
            cfg,
            instance,
            actor=user.email,
            approve=body.approve,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProcessResponse.model_validate(to_response_dict(updated))
