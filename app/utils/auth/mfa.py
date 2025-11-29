import pyotp

from app.config import config


def generate_totp_secret() -> str:
    return pyotp.random_base32()

def get_totp_uri(user_email: str,totp_secret:str, issuer_name: str = config.app_name) -> str:
    return pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=user_email, issuer_name=issuer_name
    )

def verify_totp(token: str, totp_secret: str) -> bool:
    totp = pyotp.TOTP(totp_secret)
    return totp.verify(token, valid_window=1)  # 30s tolerance