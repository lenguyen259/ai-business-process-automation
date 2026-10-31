from fastapi.testclient import TestClient


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_and_process_lifecycle(client: TestClient, auth_header: dict[str, str]):
    create = client.post(
        "/processes",
        headers=auth_header,
        json={
            "process_type": "purchase_approval",
            "payload": {
                "vendor": "Acme Supplies",
                "amount": 1200,
                "currency": "USD",
                "cost_center": "OPS-01",
                "requester_email": "buyer@example.com",
            },
        },
    )
    assert create.status_code == 201, create.text
    process_id = create.json()["id"]
    assert create.json()["status"] == "draft"
    assert create.json()["payload"]["requester_email"] == "[REDACTED_EMAIL]"

    review = client.post(f"/processes/{process_id}/ai-review", headers=auth_header)
    assert review.status_code == 200, review.text
    body = review.json()
    assert body["status"] == "pending_approval"
    assert body["ai_recommendation"] == "approve"

    decide = client.post(
        f"/processes/{process_id}/decision",
        headers=auth_header,
        json={"approve": True, "note": "Looks good"},
    )
    assert decide.status_code == 200, decide.text
    final = decide.json()
    assert final["status"] == "completed"
    assert final["external_refs"]["erp_po_id"].startswith("PO-")


def test_unauthorized_without_token(client: TestClient):
    response = client.get("/processes/1")
    assert response.status_code == 401


def test_high_value_purchase_escalates(client: TestClient, auth_header: dict[str, str]):
    create = client.post(
        "/processes",
        headers=auth_header,
        json={
            "process_type": "purchase_approval",
            "payload": {"vendor": "Big Vendor", "amount": 75000},
        },
    )
    process_id = create.json()["id"]
    review = client.post(f"/processes/{process_id}/ai-review", headers=auth_header)
    assert review.json()["ai_recommendation"] == "escalate"
