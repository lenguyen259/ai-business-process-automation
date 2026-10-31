# Architecture

## Purpose

Translate business process requirements into an executable automation service that:

1. Captures a process request via REST API
2. Runs an LLM/prompt-based advisor (with mock fallback)
3. Enforces human approval for irreversible actions
4. Integrates with ERP/CRM systems through REST web services
5. Records an immutable AI governance audit trail

## Components

| Layer | Module | Responsibility |
| --- | --- | --- |
| API | `app/main.py` | Auth, process endpoints, governance policy |
| Security | `app/security.py` | JWT auth + RBAC permissions |
| Workflow | `app/workflow.py` | State machine + approval gates |
| AI | `app/llm.py` | Prompt templates + provider adapter |
| Integration | `app/integrations.py` | ERP/CRM REST sync with retries |
| Governance | `app/governance.py` | PII redaction + audit JSONL |
| Data | `app/models.py` + SQLAlchemy | Process persistence (SQLite/SQL) |

## Process states

`draft → ai_review → pending_approval → integrating → completed|rejected|failed`

## Security & AI governance

- Bearer JWT required for mutating and sensitive read endpoints
- Role-based permissions (`admin`, `automation_engineer`, `analyst`, `viewer`)
- PII redaction before prompt construction and audit persistence
- AI recommendation is advisory; completion requires explicit decision API
- Audit events include actor, action, resource, sanitized details, policy version

## Local run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
pytest
```

Demo login:

- `engineer@example.com` / `demo-pass-123`
- `admin@example.com` / `admin-pass-123`
