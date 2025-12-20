# Auth API

A robust, asynchronous Authentication API built with **FastAPI**, **SQLModel**, and **PostgreSQL**. This project provides a complete user management system with secure authentication, Two-Factor Authentication (2FA), and email background tasks.

## 🚀 Features

*   **User Registration & Login**: Secure sign-up and sign-in processes using JWT (JSON Web Tokens).
*   **Two-Factor Authentication (2FA)**: Support for Time-based One-Time Passwords (TOTP) for enhanced security.
*   **Email Verification**: Account activation via email links to ensure valid user registration.
*   **Password Management**: Secure password hashing with Argon2, plus password reset flows.
*   **Async Database**: High-performance database interactions using SQLModel and AsyncPG.
*   **Background Tasks**: Asynchronous email sending using Celery and Redis.
*   **Modern Tooling**: Built with `uv` for dependency management and `alembic` for migrations.

## 🛠️ Tech Stack

*   **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.13+)
*   **Database**: PostgreSQL, [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy + Pydantic)
*   **Authentication**: JWT, `python-jose`, `passlib[argon2]`, `pyotp`
*   **Task Queue**: Celery, Redis
*   **Testing**: Pytest
*   **Package Manager**: [uv](https://github.com/astral-sh/uv)

## 📋 Prerequisites

Before running the project, ensure you have the following installed:

*   **Python** 3.13+
*   **PostgreSQL** (Database)
*   **Redis** (Message Broker for Celery)
*   **Make** (Optional, for using the Makefile)

## ⚙️ Installation & Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd auth_api
    ```

2.  **Set up the Virtual Environment**:
    ```bash
    make venv
    ```

3.  **Install Dependencies**:
    ```bash
    make install
    ```

4.  **Configure Environment**:
    The application uses a configuration file (e.g., `config.yaml` or `config.dev.yaml`).
    
    Ensure you have your PostgreSQL and Redis services running. Update your configuration file with the correct credentials:
    ```yaml
    database:
      url: postgresql+asyncpg://user:password@localhost/auth_api_db
    redis:
      url: redis://localhost
    ```

5.  **Run Database Migrations**:
    ```bash
    alembic upgrade head
    ```

## 🏃‍♂️ Usage

### Start the API Server
Run the development server with auto-reload:
```bash
make serve
```
The API will be available at `http://127.0.0.1:8000`.
You can access the interactive API docs at `http://127.0.0.1:8000/docs`.

### Start Celery Worker
For handling background tasks (like sending emails):
```bash
make celery
```

## 🔌 API Endpoints

### Authentication
*   **POST** `/api/auth/sign-up`: Register a new user account.
*   **POST** `/api/auth/sign-in`: Log in to receive an access token.
*   **POST** `/api/auth/sign-in-mfa`: Log in using 2FA credentials.
*   **POST** `/api/auth/access`: Refresh or retrieve access tokens.

### Account Management
*   **GET** `/api/auth/activate-account`: Activate a user account via token.
*   **POST** `/api/auth/send-activation-email`: Resend the account activation email.
*   **POST** `/api/auth/request-password-reset`: Request a password reset link.
*   **POST** `/api/auth/reset-password`: Reset the password using a valid token.

### Security (Authenticated)
*   **POST** `/api/auth/enable-2fa`: Enable Two-Factor Authentication for the current user.
*   **POST** `/api/auth/disable-2fa`: Disable Two-Factor Authentication.

## 🧪 Testing

Run the test suite using `pytest`:
```bash
make test
```

## 🧹 Code Quality

Run linting and formatting checks:
```bash
make format   # Formats code with Black and Isort
make lint     # Checks code with Flake8 and Mypy
```

## 📁 Project Structure

```
src/
├── auth/           # Authentication logic, routers, schemas
├── config/         # Configuration management
├── core/           # Core application setup & dependencies
├── entities/       # Database models (SQLModel)
├── services/       # Business logic (Service layer)
├── tasks/          # Celery tasks (e.g., email sending)
├── templates/      # Email templates (Jinja2)
└── ...
```
