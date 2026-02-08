import pytest

from src.modules.auth.util.mfa import decrypt_totp_secret, encrypt_totp_secret


def test_encrypt_decrypt_totp_secret_roundtrip():
    secret = "JBSWY3DPEHPK3PXP"
    encrypted = encrypt_totp_secret(secret)
    assert encrypted != secret
    assert decrypt_totp_secret(encrypted) == secret


def test_decrypt_invalid_secret_raises():
    with pytest.raises(ValueError):
        decrypt_totp_secret("not-a-valid-token")
