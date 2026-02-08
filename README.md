# Auth API

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLModel](https://img.shields.io/badge/SQLModel-0.0.14+-009688.svg)](https://sqlmodel.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production‑ready authentication service built with FastAPI, SQLModel, and PostgreSQL. It supports account activation, password resets, MFA (TOTP), refresh token rotation, and per‑device sessions with session revocation.

## Architecture

```mermaid
graph TD
    User([User]) <--> API[FastAPI Server]
    API <--> DB[(PostgreSQL)]
    API <--> Redis[(Redis)]
    Redis <--> Worker[Celery Worker]
    Worker --> Email[Email Service]
```

## Features

- JWT sign‑up/sign‑in with refresh rotation
- Per‑device sessions (refresh tokens are session‑bound)
- MFA (TOTP) with encrypted secrets at rest
- Account activation and password reset via email
- Session revocation: single session or all sessions
- Admin revoke sessions by user ID
- Async DB + background email tasks

## Tech Stack

- FastAPI
- SQLModel + PostgreSQL
- Redis + Celery
- python‑jose (JWT), pwdlib (password hashing), pyotp (TOTP)
- uv + Alembic + Pytest

## Prerequisites

- Python 3.13+
- PostgreSQL
- Redis
- uv

## Quickstart

1. Install dependencies

```bash
make venv
```

2. Configure settings

This project uses `config.yaml` (or `config.dev.yaml` / `config.test.yaml`). Review and update:

- `token.secret_key` (JWT and refresh hash secret)
- `totp_secret_key` (optional, for encrypting TOTP secrets; falls back to `token.secret_key`)
- `database` and `redis` URLs
- `smtp_server` settings
- `api_key` for admin endpoints

3. Migrate database

```bash
uv run alembic upgrade head
```

4. Run the API

```bash
make serve
```

## API Overview

All endpoints are under `/api`.

### Auth

- `POST /api/auth/sign-up`
- `POST /api/auth/sign-in`
- `POST /api/auth/sign-in-mfa`
- `POST /api/auth/activate-account`
- `POST /api/auth/request-password-reset`
- `POST /api/auth/reset-password`
- `POST /api/auth/access` (refresh rotation)
- `POST /api/auth/enable-2fa`
- `POST /api/auth/disable-2fa`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `GET /api/auth/sessions`
- `POST /api/auth/change-email`
- `POST /api/auth/admin/revoke-sessions/{user_id}` (admin only)

### Example: Sign In

```bash
curl -X POST http://localhost:3000/api/auth/sign-in \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"CorrectHorseBatteryStaple1!"}'
```

### Example: MFA Sign In

```bash
curl -X POST http://localhost:3000/api/auth/sign-in-mfa \
  -H 'Content-Type: application/json' \
  -d '{"token":"<temp_2fa_token>","totp_token":"123456"}'
```

### Example: Refresh Rotation

```bash
curl -X POST http://localhost:3000/api/auth/access \
  -H 'Content-Type: application/json' \
  -d '{"token":"<refresh_token>"}'
```

Response:

```json
{
  "access_token": {"token": "<access>", "duration": "2026-02-08T16:00:00Z"},
  "refresh_token": {"token": "<refresh>", "duration": "2026-03-08T16:00:00Z"}
}
```

### Example: Logout (single session)

```bash
curl -X POST http://localhost:3000/api/auth/logout \
  -H 'Content-Type: application/json' \
  -d '{"token":"<refresh_token>"}'
```

### Example: Logout All

```bash
curl -X POST http://localhost:3000/api/auth/logout-all \
  -H 'Authorization: Bearer <access_token>'
```

### Example: List Sessions

```bash
curl -X GET http://localhost:3000/api/auth/sessions \
  -H 'Authorization: Bearer <access_token>'
```

### Example: Change Email

```bash
curl -X POST http://localhost:3000/api/auth/change-email \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"new_email":"alice2@example.com","password":"CorrectHorseBatteryStaple1!"}'
```

### Example: Admin Revoke Sessions

```bash
curl -X POST http://localhost:3000/api/auth/admin/revoke-sessions/123 \
  -H 'X-API-Key: <admin_api_key>'
```

## Session Model

Refresh tokens are tied to a server‑side session record. On refresh:

- The refresh token must match the stored hash for the session
- A new refresh token is issued with a new `jti`
- The session hash is updated

Revocations set `revoked_at` and invalidate refresh and access tokens for that session.

## Security Notes

- Set `token.secret_key` and `totp_secret_key` to strong values.
- Admin endpoints require `X-API-Key` set to `config.env.api_key`.
- TOTP secrets are encrypted before storing in DB.

## Testing

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest
```

## Project Layout

```text
src/
├── core/           # Dependencies, middleware, celery setup
├── config/         # App configuration management
├── modules/        # Domain modules
│   └── auth/       # Auth domain (models, routers, services)
├── tasks/          # Celery tasks
├── templates/      # Email templates
└── shared/         # Common utilities
```

## License

MIT
