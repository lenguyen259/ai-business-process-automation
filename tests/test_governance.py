from app.governance import governance_checklist, redact_pii, sanitize_payload


def test_redact_pii_email_and_phone():
    text = "Contact jane.doe@example.com or +84-398-599-174"
    redacted = redact_pii(text)
    assert "jane.doe@example.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted


def test_sanitize_payload_nested():
    payload = {"owner_email": "a@b.com", "nested": {"phone": "0909123456"}}
    cleaned = sanitize_payload(payload, enabled=True)
    assert cleaned["owner_email"] == "[REDACTED_EMAIL]"
    assert cleaned["nested"]["phone"] == "[REDACTED_PHONE]"


def test_governance_checklist_contains_rbac():
    policy = governance_checklist()
    assert policy["policy_version"] == "ai-governance-v1"
    assert any("RBAC" in item or "role-based" in item for item in policy["controls"])
