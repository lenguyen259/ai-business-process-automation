# API overview

## Auth

`POST /auth/login`

```json
{"email": "engineer@example.com", "password": "demo-pass-123"}
```

Returns `access_token` for `Authorization: Bearer <token>`.

## Process automation

1. `POST /processes` — create process instance
2. `POST /processes/{id}/ai-review` — run LLM/mock advisor
3. `POST /processes/{id}/decision` — approve/reject + integrate
4. `GET /processes/{id}` — inspect status and external refs

## Governance

`GET /governance/policy` — published controls for access, privacy, and AI usage.
