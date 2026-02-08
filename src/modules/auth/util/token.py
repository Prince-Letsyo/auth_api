from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from typing import Any, cast

from jose import jwt

from src.modules.auth.schemas.token import JWTPayload, JWTPayloadWithExp
from src.config import config

SECRET_KEY: str = config.env.token.secret_key
ALGORITHM: str = config.env.token.algorithm

ACCESS_TOKEN_EXPIRE_MINUTES: int = config.env.token.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_WEEKS: int = config.env.token.refresh_token_expire_weeks


class JWTAuthToken:
    """Creates refresh and access tokens"""

    def __create_token(
        self,
        data: JWTPayload,
        expires_delta: timedelta | None = None,
        token_type: str | None = None,
    ) -> tuple[str, datetime]:
        """Create JWT token string

        Args:
            data (JWTPayload): payload
            expires_delta (timedelta | None, optional): Token duration of existing. Defaults to None.

        Returns:
           tuple[str, datetime]: token string and expiration datetime
        """
        to_encode: JWTPayload = data.copy()
        if expires_delta:
            expire: datetime = (  # pyright: ignore[reportRedeclaration]
                datetime.now(timezone.utc) + expires_delta
            )
        else:
            expire: datetime = datetime.now(timezone.utc) + timedelta(minutes=15)
        claims: JWTPayloadWithExp = cast(JWTPayloadWithExp, to_encode)
        if token_type:
            claims.update({"token_type": token_type})
        claims.update({"exp": expire})
        encoded_jwt = jwt.encode(
            claims=dict(claims),
            key=SECRET_KEY,
            algorithm=ALGORITHM,
        )

        return encoded_jwt, expire

    def activate_token(self, data: JWTPayload) -> tuple[str, datetime]:
        """Create account activation JWT token that should last for about 15 minutes

        Args:
            data (JWTPayload): payload
            expires_delta (timedelta | None, optional): Token duration of existing. Defaults to None.
        Returns:
            tuple[str, datetime]: token string and expiration datetime
        """
        return self.__create_token(data, token_type="activate")

    def password_reset_token(self, data: JWTPayload) -> tuple[str, datetime]:
        """Create password reset JWT token that should last for about 15 minutes

        Args:
            data (JWTPayload): payload
        Returns:
            tuple[str, datetime]: token string and expiration datetime
        """
        return self.__create_token(data, token_type="password_reset")

    def access_token(self, data: JWTPayload) -> tuple[str, datetime]:
        """Create access JWT access token that should last for about a 30 minutes

        Args:
            data (JWTPayload): payload
            expires_delta (timedelta | None, optional): Token duration of existing. Defaults to None.

        Returns:
            tuple[str, datetime]: token string and expiration datetime
        """
        return self.__create_token(
            data,
            expires_delta=timedelta(minutes=float(ACCESS_TOKEN_EXPIRE_MINUTES)),
            token_type="access",
        )

    def refresh_token(self, data: JWTPayload) -> tuple[str, datetime]:
        """Create refresh JWT access token that should last for about a month

        Args:
            data (JWTPayload): payload
            expires_delta (timedelta | None, optional): Token duration of existing. Defaults to None.

        Returns:
            tuple[str, datetime]: token string and expiration datetime
        """
        return self.__create_token(
            data,
            expires_delta=timedelta(weeks=float(REFRESH_TOKEN_EXPIRE_WEEKS)),
            token_type="refresh",
        )

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decodes all types of tokens.

        Args:
            token (str): Accepts access or refresh token string.

        Raises:
            ExpiredSignatureError: If the token has expired.
            JWTError: If the token is invalid or malformed.

        Returns:
            dict[str, Any]: The decoded JWT payload.
        """
        try:
            payload: dict[str, Any] = jwt.decode(  # pyright: ignore[reportExplicitAny]
                token, SECRET_KEY, algorithms=[ALGORITHM]
            )
            return payload
        except (ExpiredSignatureError, JWTError) as e:
            # We re-raise these specifically so callers can handle them if needed,
            # but they inherit from JWTError or are checked explicitly in controllers.
            raise e
        except Exception as e:
            # Wrap unexpected errors in a general JWTError to maintain consistency
            raise JWTError("An unexpected error occurred during token decoding") from e

    def create_temp_2fa_token(self, data: JWTPayload) -> tuple[str, datetime]:
        """Create temporary 2FA JWT token that should last for about 5 minutes

        Args:
            data (JWTPayload): payload
        Returns:
            tuple[str, datetime]: token string and expiration datetime
        """
        return self.__create_token(
            data,
            expires_delta=timedelta(
                minutes=float(config.env.token.temp_2fa_token_expire_minutes)
            ),
            token_type="temp_2fa",
        )


jwt_auth_token: JWTAuthToken = JWTAuthToken()


def hash_token(token: str) -> str:
    return hmac.new(SECRET_KEY.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()
