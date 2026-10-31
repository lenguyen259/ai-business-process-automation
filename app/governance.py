"""AI governance helpers: audit trail, PII redaction, policy checks."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b")
NATIONAL_ID_RE = re.compile(r"\b\d{9,12}\b")


def redact_pii(text: str) -> str:
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = NATIONAL_ID_RE.sub("[REDACTED_ID]", text)
    return text


def sanitize_payload(payload: dict[str, Any], enabled: bool = True) -> dict[str, Any]:
    if not enabled:
        return payload

    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            cleaned[key] = redact_pii(value)
        elif isinstance(value, dict):
            cleaned[key] = sanitize_payload(value, enabled=True)
        elif isinstance(value, list):
            cleaned[key] = [
                sanitize_payload(item, enabled=True)
                if isinstance(item, dict)
                else redact_pii(item)
                if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


def append_audit_event(
    settings: Settings,
    *,
    actor: str,
    action: str,
    resource: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "resource": resource,
        "details": sanitize_payload(details or {}, enabled=settings.enable_pii_redaction),
        "policy_version": "ai-governance-v1",
    }
    path = Path(settings.audit_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def governance_checklist() -> dict[str, Any]:
    return {
        "policy_version": "ai-governance-v1",
        "controls": [
            "role-based access control (RBAC)",
            "JWT authentication for all mutating endpoints",
            "PII redaction before LLM prompts and audit storage",
            "human approval gate for high-risk process transitions",
            "immutable JSONL audit trail for AI decisions",
            "prompt templates versioned and reviewable",
        ],
        "data_retention": "Process payloads retained 90 days; audit logs 365 days",
        "model_usage": "LLM outputs are advisory; irreversible actions require approval",
    }
