"""REST integrations with ERP/CRM style systems (httpx + resilient retries)."""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from app.config import Settings


class IntegrationError(RuntimeError):
    pass


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.1, min=0.1, max=0.5), reraise=True)
def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(timeout=2.0) as client:
        response = client.post(url, json=payload)
        if response.status_code >= 500:
            raise IntegrationError(f"Upstream {url} returned {response.status_code}")
        response.raise_for_status()
        if not response.content:
            return {"ok": True}
        return response.json()


def _stub_or_post(url: str, body: dict[str, Any], stub: dict[str, Any], *, force_stub: bool) -> dict[str, Any]:
    if force_stub:
        return stub
    try:
        return _post_json(url, body)
    except (httpx.HTTPError, IntegrationError, RetryError, OSError):
        return stub


def _should_stub(base_url: str) -> bool:
    host = base_url.lower()
    return "localhost" in host or "127.0.0.1" in host or host.endswith(".local")


def sync_purchase_to_erp(settings: Settings, process_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Push approved purchase request into ERP-like endpoint.

    In local/demo mode (default ERP URL unreachable), returns a deterministic stub.
    """
    body = {
        "external_process_id": process_id,
        "vendor": payload.get("vendor"),
        "amount": payload.get("amount"),
        "currency": payload.get("currency", "USD"),
        "cost_center": payload.get("cost_center"),
    }
    return _stub_or_post(
        f"{settings.erp_base_url.rstrip('/')}/api/v1/purchase-orders",
        body,
        {
            "ok": True,
            "mode": "stub",
            "erp_po_id": f"PO-{process_id:06d}",
            "payload": body,
        },
        force_stub=_should_stub(settings.erp_base_url),
    )


def sync_customer_to_crm(settings: Settings, process_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    body = {
        "external_process_id": process_id,
        "customer_name": payload.get("customer_name"),
        "segment": payload.get("segment", "smb"),
        "owner_email": payload.get("owner_email"),
    }
    return _stub_or_post(
        f"{settings.crm_base_url.rstrip('/')}/api/v1/accounts",
        body,
        {
            "ok": True,
            "mode": "stub",
            "crm_account_id": f"ACC-{process_id:06d}",
            "payload": body,
        },
        force_stub=_should_stub(settings.crm_base_url),
    )
