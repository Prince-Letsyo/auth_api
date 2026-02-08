import base64
import hashlib

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from src.config import config


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(
    user_email: str, totp_secret: str, issuer_name: str = config.app_name
) -> str:
    return pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=user_email, issuer_name=issuer_name
    )


def verify_totp(token: str, totp_secret: str) -> bool:
    totp = pyotp.TOTP(totp_secret)
    return totp.verify(token, valid_window=1)  # 30s tolerance


def _get_fernet() -> Fernet:
    key_material = config.env.totp_secret_key or config.env.token.secret_key
    if not key_material:
        raise RuntimeError("TOTP secret key material is not configured")
    digest = hashlib.sha256(key_material.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_totp_secret(totp_secret: str) -> str:
    fernet = _get_fernet()
    return fernet.encrypt(totp_secret.encode("utf-8")).decode("utf-8")


def decrypt_totp_secret(encrypted_secret: str) -> str:
    fernet = _get_fernet()
    try:
        return fernet.decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted TOTP secret") from exc
