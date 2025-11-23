from datetime import timedelta, datetime, timezone
from jose import jwt
from app.config import config
from typing import Any, TypedDict, cast

SECRET_KEY: str = config.env.SECRET_KEY
ALGORITHM: str = config.env.ALGORITHM

ACCESS_TOKEN_EXPIRE_MINUTES: int = config.env.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_WEEKS: int = config.env.REFRESH_TOKEN_EXPIRE_WEEKS


class JWTPayload(TypedDict):
    username: str
    email: str
    user_id:int


class JWTPayloadWithExp(JWTPayload):
    exp: datetime


class JWTAuthToken:
    """Creates refresh and access tokens"""

    def __create_token(
        self, data: JWTPayload, expires_delta: timedelta | None = None
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
        return self.__create_token(data)

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
        )

    def decode_token(self, token: str) -> dict[str, str]:
        """Decodes all types of tokens

        Args:
            token (str): Accepts access or refresh token

        Raises:
            e: Exceptions

        Returns:
            dict[str, str]: Payload
        """
        try:
            payload: dict[str, Any] = jwt.decode(  # pyright: ignore[reportExplicitAny]
                token, SECRET_KEY, algorithms=[ALGORITHM]
            )
            return payload
        except Exception as e:
            raise e


jwt_auth_token: JWTAuthToken = JWTAuthToken()
