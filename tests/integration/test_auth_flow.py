import pyotp

from src.modules.auth.util.token import jwt_auth_token


def test_signup_activate_login_and_refresh(client, activated_user):
    response = client.post(
        "/api/auth/sign-in",
        json={"username": "shared", "password": "SharedCorrectHorseBatteryStaple1!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requires_2fa"] is False
    access_token = body["token"]["access_token"]["token"]
    refresh_token = body["token"]["refresh_token"]["token"]

    response = client.post(
        "/api/auth/access",
        json={"token": refresh_token},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]["token"]
    assert body["refresh_token"]["token"]

def test_enable_2fa_and_sign_in_mfa(client, mfa_user):
    secret = mfa_user["secret"]
    response = client.post(
        "/api/auth/sign-in",
        json={"username": "mfa_user", "password": "MfaCorrectHorseBatteryStaple1!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requires_2fa"] is True
    temp_token = body["token"]["token"]

    totp = pyotp.TOTP(secret).now()
    response = client.post(
        "/api/auth/sign-in-mfa",
        json={"token": temp_token, "totp_token": totp},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requires_2fa"] is False
    assert body["token"]["access_token"]["token"]


def test_login_with_wrong_password(client, activated_user):
    response = client.post(
        "/api/auth/sign-in",
        json={"username": "shared", "password": "WrongPassword1!"},
    )
    assert response.status_code in {400, 401, 404}


def test_activate_with_wrong_token_type(client, activated_user):
    response = client.post(
        "/api/auth/sign-in",
        json={"username": "shared", "password": "SharedCorrectHorseBatteryStaple1!"},
    )
    assert response.status_code == 200
    access_token = response.json()["token"]["access_token"]["token"]
    response = client.get(f"/api/auth/activate-account?token={access_token}")
    assert response.status_code == 401


def test_refresh_with_access_token_fails(client, activated_user):
    response = client.post(
        "/api/auth/sign-in",
        json={"username": "shared", "password": "SharedCorrectHorseBatteryStaple1!"},
    )
    assert response.status_code == 200
    access_token = response.json()["token"]["access_token"]["token"]

    response = client.post(
        "/api/auth/access",
        json={"token": access_token},
    )
    assert response.status_code == 401


def test_access_token_from_refresh_token(client, refresh_token_user):
    refresh_token = refresh_token_user["refresh_token"]
    response = client.post(
        "/api/auth/access",
        json={"token": refresh_token},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]["token"]
    assert body["refresh_token"]["token"]


def test_refresh_token_rotation(client, refresh_token_user):
    refresh_token = refresh_token_user["refresh_token"]
    response = client.post(
        "/api/auth/access",
        json={"token": refresh_token},
    )
    assert response.status_code == 200
    rotated = response.json()
    new_refresh = rotated["refresh_token"]["token"]

    response = client.post(
        "/api/auth/access",
        json={"token": refresh_token},
    )
    assert response.status_code == 401

    response = client.post(
        "/api/auth/access",
        json={"token": new_refresh},
    )
    assert response.status_code == 200


def test_logout_revoke_single_session(client, refresh_token_user):
    refresh_token = refresh_token_user["refresh_token"]
    response = client.post(
        "/api/auth/logout",
        json={"token": refresh_token},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/auth/access",
        json={"token": refresh_token},
    )
    assert response.status_code == 401


def test_logout_all_sessions(client, refresh_token_user):
    response = client.post(
        "/api/auth/sign-in",
        json={
            "username": "refresh_user",
            "password": "RefreshCorrectHorseBatteryStaple1!",
        },
    )
    assert response.status_code == 200
    access_token = response.json()["token"]["access_token"]["token"]
    refresh_token = response.json()["token"]["refresh_token"]["token"]

    response = client.post(
        "/api/auth/logout-all",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/auth/access",
        json={"token": refresh_token},
    )
    assert response.status_code == 401


def test_list_sessions(client, refresh_token_user):
    response = client.post(
        "/api/auth/sign-in",
        json={
            "username": "refresh_user",
            "password": "RefreshCorrectHorseBatteryStaple1!",
        },
    )
    assert response.status_code == 200
    access_token = response.json()["token"]["access_token"]["token"]

    response = client.get(
        "/api/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    sessions = response.json()
    assert isinstance(sessions, list)
    assert sessions
    assert sessions[0]["id"]


def test_change_email_revokes_sessions(client, user_factory):
    user_factory(
        username="email_change_user",
        email="email_change_user@example.com",
        password="EmailChangeCorrectHorseBatteryStaple1!",
    )
    response = client.post(
        "/api/auth/sign-in",
        json={
            "username": "email_change_user",
            "password": "EmailChangeCorrectHorseBatteryStaple1!",
        },
    )
    assert response.status_code == 200
    access_token = response.json()["token"]["access_token"]["token"]
    refresh_token = response.json()["token"]["refresh_token"]["token"]

    response = client.post(
        "/api/auth/change-email",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "new_email": "email_change_user2@example.com",
            "password": "EmailChangeCorrectHorseBatteryStaple1!",
        },
    )
    assert response.status_code == 200

    response = client.post(
        "/api/auth/access",
        json={"token": refresh_token},
    )
    assert response.status_code == 401


def test_admin_revoke_sessions(client, refresh_token_user):
    response = client.post(
        "/api/auth/sign-in",
        json={
            "username": "refresh_user",
            "password": "RefreshCorrectHorseBatteryStaple1!",
        },
    )
    assert response.status_code == 200
    refresh_token = response.json()["token"]["refresh_token"]["token"]
    user_id = refresh_token_user["user"].id

    response = client.post(
        f"/api/auth/admin/revoke-sessions/{user_id}",
        headers={"X-API-Key": "sk-your-api-key-here"},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/auth/access",
        json={"token": refresh_token},
    )
    assert response.status_code == 401


def test_mfa_with_invalid_totp_fails(client, mfa_user):
    response = client.post(
        "/api/auth/sign-in",
        json={"username": "mfa_user", "password": "MfaCorrectHorseBatteryStaple1!"},
    )
    assert response.status_code == 200
    temp_token = response.json()["token"]["token"]

    response = client.post(
        "/api/auth/sign-in-mfa",
        json={"token": temp_token, "totp_token": "000000"},
    )
    assert response.status_code == 401


def test_password_reset_flow_and_wrong_token_type(client, password_reset_user):
    password_reset_token = password_reset_user["password_reset_token"]
    response = client.post(
        "/api/auth/sign-in",
        json={"username": "reset_user", "password": "ResetCorrectHorseBatteryStaple1!"},
    )
    assert response.status_code == 200
    old_refresh_token = response.json()["token"]["refresh_token"]["token"]
    response = client.post(
        "/api/auth/request-password-reset",
        json={"email": "reset_user@example.com"},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/auth/reset-password",
        json={
            "token": password_reset_token,
            "email": "reset_user@example.com",
            "password_one": "NewCorrectHorseBatteryStaple1!",
            "password_two": "NewCorrectHorseBatteryStaple1!",
        },
    )
    assert response.status_code == 200

    response = client.post(
        "/api/auth/access",
        json={"token": old_refresh_token},
    )
    assert response.status_code == 401

    response = client.post(
        "/api/auth/sign-in",
        json={"username": "reset_user", "password": "NewCorrectHorseBatteryStaple1!"},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/auth/sign-in",
        json={"username": "reset_user", "password": "ResetCorrectHorseBatteryStaple1!"},
    )
    assert response.status_code in {400, 401, 404}

    response = client.post(
        "/api/auth/sign-in",
        json={"username": "reset_user", "password": "NewCorrectHorseBatteryStaple1!"},
    )
    assert response.status_code == 200
    access_token = response.json()["token"]["access_token"]["token"]

    response = client.post(
        "/api/auth/reset-password",
        json={
            "token": access_token,
            "email": "reset_user@example.com",
            "password_one": "AnotherCorrectHorseBatteryStaple1!",
            "password_two": "AnotherCorrectHorseBatteryStaple1!",
        },
    )
    assert response.status_code == 401


def test_resend_activation_email(client):
    response = client.post(
        "/api/auth/sign-up",
        json={
            "username": "hank",
            "email": "hank@example.com",
            "password_one": "CorrectHorseBatteryStaple1!",
            "password_two": "CorrectHorseBatteryStaple1!",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/api/auth/send-activation-email",
        json={"email": "hank@example.com"},
    )
    assert response.status_code == 200
