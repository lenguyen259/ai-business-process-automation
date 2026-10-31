"""Prompt-engineered LLM advisor with mock + HTTP providers."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings
from app.governance import redact_pii
from app.schemas import ProcessType

PROMPT_VERSION = "process-advisor-v1"

SYSTEM_PROMPT = """You are an enterprise AI process advisor.
Return ONLY compact JSON with keys: recommendation (approve|reject|escalate),
confidence (0-1), rationale (short), risk_flags (array of strings).
Never invent facts outside the provided payload. Prefer escalate when unsure.
"""


def build_user_prompt(process_type: ProcessType, payload: dict[str, Any]) -> str:
    safe_payload = {k: redact_pii(str(v)) if isinstance(v, str) else v for k, v in payload.items()}
    return (
        f"prompt_version={PROMPT_VERSION}\n"
        f"process_type={process_type.value}\n"
        f"payload={json.dumps(safe_payload, ensure_ascii=False)}\n"
        "Decide the next recommended action for this business process."
    )


def _mock_decision(process_type: ProcessType, payload: dict[str, Any]) -> dict[str, Any]:
    amount = float(payload.get("amount", 0) or 0)
    priority = str(payload.get("priority", "medium")).lower()

    if process_type == ProcessType.PURCHASE_APPROVAL:
        if amount >= 50000:
            return {
                "recommendation": "escalate",
                "confidence": 0.91,
                "rationale": "High-value purchase requires human approval.",
                "risk_flags": ["high_value"],
            }
        if amount <= 0:
            return {
                "recommendation": "reject",
                "confidence": 0.97,
                "rationale": "Invalid purchase amount.",
                "risk_flags": ["invalid_amount"],
            }
        return {
            "recommendation": "approve",
            "confidence": 0.88,
            "rationale": "Amount within auto-approval threshold.",
            "risk_flags": [],
        }

    if process_type == ProcessType.INCIDENT_TRIAGE and priority in {"critical", "high"}:
        return {
            "recommendation": "escalate",
            "confidence": 0.9,
            "rationale": "High-priority incident needs on-call review.",
            "risk_flags": ["sla_risk"],
        }

    return {
        "recommendation": "approve",
        "confidence": 0.8,
        "rationale": "Standard process path looks safe to continue.",
        "risk_flags": [],
    }


def advise(settings: Settings, process_type: ProcessType, payload: dict[str, Any]) -> dict[str, Any]:
    if settings.llm_provider == "mock" or not settings.llm_api_key:
        return _mock_decision(process_type, payload)

    body = {
        "model": settings.llm_model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(process_type, payload)},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{settings.llm_api_base.rstrip('/')}/chat/completions",
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
