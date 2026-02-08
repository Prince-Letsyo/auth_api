# Auth API

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLModel](https://img.shields.io/badge/SQLModel-0.0.14+-009688.svg)](https://sqlmodel.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A robust, asynchronous Authentication API built with **FastAPI**, **SQLModel**, and **PostgreSQL**. This project provides a complete user management system with secure authentication, Two-Factor Authentication (2FA), and email background tasks.

## 🏗️ Architecture

```mermaid
graph TD
    User([User]) <--> API[FastAPI Server]
    API <--> DB[(PostgreSQL)]
    API <--> Redis[(Redis)]
    Redis <--> Worker[Celery Worker]
    Worker --> Email[Email Service]
```

## 🚀 Features

*   **Secure Authentication**: JWT-based sign-up, sign-in, and token refresh.
*   **Two-Factor Authentication (2FA)**: Support for TOTP using apps like Google Authenticator.
*   **Account Activation**: Email-based verification for new accounts.
*   **Password Management**: Argon2 hashing and secure reset flows.
*   **Async Performance**: Fully asynchronous database and API operations.
*   **Background Tasks**: Celery-powered email delivery.
*   **Modern Tooling**: Managed with `uv` and `alembic` for migrations.

## 🛠️ Tech Stack

*   **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
*   **Database**: PostgreSQL with [SQLModel](https://sqlmodel.tiangolo.com/)
*   **Auth**: JWT (python-jose), Argon2 (passlib), TOTP (pyotp)
*   **Task Queue**: Celery & Redis
*   **Tooling**: [uv](https://github.com/astral-sh/uv), Alembic, Pytest

## 📋 Prerequisites

- Python 3.13+
- PostgreSQL
- Redis
- [uv](https://github.com/astral-sh/uv) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## ⚙️ Setup & Installation

1.  **Clone the Repository**
    ```bash
    git clone <repository-url>
    cd auth_api
    ```

2.  **Initialize Environment**
    ```bash
    make venv
    ```

3.  **Configure Environment Variables**
    Copy `.env.example` to `.env` (if applicable) or create a `.env` file with:
    ```env
    SECRET_KEY=your-secure-secret
    DB_URL=postgresql+asyncpg://user:password@localhost/auth_api_db
    REDIS_URL=redis://localhost
    CELERY_BROKER_URL=redis://localhost:6379/0
    ```

4.  **Run Migrations**
    ```bash
    alembic upgrade head
    ```

## 🏃‍♂️ Development

| Command | Description |
|---------|-------------|
| `make serve` | Start the API server (auto-reload) |
| `make celery` | Start the Celery worker |
| `make test` | Run the test suite |
| `make lint` | Run quality checks (Flake8, Mypy) |
| `make format` | Format code (Black, Isort) |

## 📁 Project Structure

```text
src/
├── core/           # Security, dependencies, celery setup
├── config/         # App configuration management
├── modules/        # Domain-driven modules
│   └── auth/       # Authentication domain (models, routers, services)
├── tasks/          # Celery background tasks
├── templates/      # Jinja2 email templates
└── shared/         # Common utilities and base classes
```

## 🔌 API Overview

### Auth Endpoints
- `POST /api/auth/sign-up`: Register new user
- `POST /api/auth/sign-in`: Login (non-MFA)
- `POST /api/auth/sign-in-mfa`: Login with 2FA
- `POST /api/auth/enable-2fa`: Setup TOTP
- `POST /api/auth/activate-account`: Email verification

Access the interactive documentation at `/docs` (Swagger) or `/redoc`.

## 🧪 Testing

Tests are located in the `tests/` directory and can be run using:
```bash
make test
```

