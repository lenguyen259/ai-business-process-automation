"""Business process state machine with AI advisory + human approval gates."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.governance import append_audit_event, sanitize_payload
from app.integrations import sync_customer_to_crm, sync_purchase_to_erp
from app.llm import advise
from app.models import ProcessInstance
from app.schemas import ProcessStatus, ProcessType


HIGH_RISK_RECOMMENDATIONS = {"escalate", "reject"}


def _dumps(data: dict[str, Any] | None) -> str | None:
    if data is None:
        return None
    return json.dumps(data, ensure_ascii=False)


def _loads(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    return json.loads(raw)


def create_process(
    db: Session,
    settings: Settings,
    *,
    process_type: ProcessType,
    requester: str,
    payload: dict[str, Any],
) -> ProcessInstance:
    safe_payload = sanitize_payload(payload, enabled=settings.enable_pii_redaction)
    instance = ProcessInstance(
        process_type=process_type.value,
        status=ProcessStatus.DRAFT.value,
        requester=requester,
        payload_json=_dumps(safe_payload) or "{}",
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    append_audit_event(
        settings,
        actor=requester,
        action="process.create",
        resource=f"process:{instance.id}",
        details={"process_type": process_type.value},
    )
    return instance


def run_ai_review(db: Session, settings: Settings, instance: ProcessInstance, actor: str) -> ProcessInstance:
    process_type = ProcessType(instance.process_type)
    payload = _loads(instance.payload_json)
    decision = advise(settings, process_type, payload)

    instance.ai_recommendation = decision.get("recommendation")
    instance.ai_rationale = decision.get("rationale")
    instance.status = ProcessStatus.AI_REVIEW.value

    if decision.get("recommendation") == "approve" and float(decision.get("confidence", 0)) >= 0.85:
        # Low-risk auto path still requires explicit approve endpoint for governance.
        instance.status = ProcessStatus.PENDING_APPROVAL.value
    else:
        instance.status = ProcessStatus.PENDING_APPROVAL.value

    db.add(instance)
    db.commit()
    db.refresh(instance)

    append_audit_event(
        settings,
        actor=actor,
        action="process.ai_review",
        resource=f"process:{instance.id}",
        details={
            "recommendation": instance.ai_recommendation,
            "rationale": instance.ai_rationale,
            "confidence": decision.get("confidence"),
            "risk_flags": decision.get("risk_flags", []),
        },
    )
    return instance


def apply_human_decision(
    db: Session,
    settings: Settings,
    instance: ProcessInstance,
    *,
    actor: str,
    approve: bool,
    note: str | None = None,
) -> ProcessInstance:
    if instance.status != ProcessStatus.PENDING_APPROVAL.value:
        raise ValueError("Process is not awaiting approval")

    if not approve:
        instance.status = ProcessStatus.REJECTED.value
        db.add(instance)
        db.commit()
        db.refresh(instance)
        append_audit_event(
            settings,
            actor=actor,
            action="process.reject",
            resource=f"process:{instance.id}",
            details={"note": note},
        )
        return instance

    instance.status = ProcessStatus.INTEGRATING.value
    db.add(instance)
    db.commit()

    payload = _loads(instance.payload_json)
    process_type = ProcessType(instance.process_type)
    try:
        if process_type == ProcessType.PURCHASE_APPROVAL:
            refs = sync_purchase_to_erp(settings, instance.id, payload)
        elif process_type == ProcessType.CUSTOMER_ONBOARDING:
            refs = sync_customer_to_crm(settings, instance.id, payload)
        else:
            refs = {"ok": True, "mode": "no_external_sync"}
        instance.external_refs_json = _dumps(refs)
        instance.status = ProcessStatus.COMPLETED.value
    except Exception as exc:  # noqa: BLE001 - captured into process status for operators
        instance.status = ProcessStatus.FAILED.value
        instance.external_refs_json = _dumps({"error": str(exc)})

    db.add(instance)
    db.commit()
    db.refresh(instance)
    append_audit_event(
        settings,
        actor=actor,
        action="process.approve_and_integrate",
        resource=f"process:{instance.id}",
        details={"note": note, "status": instance.status, "refs": _loads(instance.external_refs_json)},
    )
    return instance


def to_response_dict(instance: ProcessInstance) -> dict[str, Any]:
    return {
        "id": instance.id,
        "process_type": instance.process_type,
        "status": instance.status,
        "requester": instance.requester,
        "payload": _loads(instance.payload_json),
        "ai_recommendation": instance.ai_recommendation,
        "ai_rationale": instance.ai_rationale,
        "external_refs": _loads(instance.external_refs_json) or None,
        "created_at": instance.created_at,
        "updated_at": instance.updated_at,
    }
