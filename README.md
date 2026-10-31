# AI Business Process Automation

Production-style PoC for **AI-powered business process automation**: design → develop → test → deploy workflows that combine LLM advisors, human approval gates, SQL persistence, and REST integrations with ERP/CRM systems.

Built to demonstrate the skill set expected of an **AI & Automation Engineer**:

- Translate business requirements into technical workflows
- Automate purchase approval, customer onboarding, and incident triage
- Integrate with existing systems via REST APIs
- Enforce data security, privacy (PII redaction), access control (RBAC/JWT), and AI governance
- Ship unit/integration tests and technical documentation

## Quick start

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

```powershell
pytest
```

Open docs: `http://localhost:8000/docs`

### Demo credentials

| User | Password | Role |
| --- | --- | --- |
| `engineer@example.com` | `demo-pass-123` | automation_engineer |
| `admin@example.com` | `admin-pass-123` | admin |

## Example flow

```powershell
# 1) Login
$token = (Invoke-RestMethod -Method POST http://localhost:8000/auth/login -ContentType 'application/json' -Body '{"email":"engineer@example.com","password":"demo-pass-123"}').access_token
$headers = @{ Authorization = "Bearer $token" }

# 2) Create process
$created = Invoke-RestMethod -Method POST http://localhost:8000/processes -Headers $headers -ContentType 'application/json' -Body '{"process_type":"purchase_approval","payload":{"vendor":"Acme","amount":1200,"currency":"USD","cost_center":"OPS-01","requester_email":"buyer@example.com"}}'

# 3) AI review + approve
Invoke-RestMethod -Method POST "http://localhost:8000/processes/$($created.id)/ai-review" -Headers $headers
Invoke-RestMethod -Method POST "http://localhost:8000/processes/$($created.id)/decision" -Headers $headers -ContentType 'application/json' -Body '{"approve":true,"note":"ok"}'
```

## Stack

Python, FastAPI, SQLAlchemy/SQLite (SQL), JWT/RBAC, httpx, tenacity, Pydantic, Pytest, Docker.

## Docs

- [Architecture](docs/architecture.md)
- [API](docs/api.md)

## License

MIT
