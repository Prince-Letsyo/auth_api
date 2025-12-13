
class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, *args: object) -> None:
        self.message: str = message
        self.status_code: int = status_code
        super().__init__(*args)


class ConflictException(AppException):
    """For conflict keys."""

    def __init__(self, message: str = "Conflict keys") -> None:
        super().__init__(message, status_code=409)

class NotFoundException(AppException):
    """For missing resources."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404)


class UnauthorizedException(AppException):
    """For authentication errors."""

    def __init__(self, message: str = "Unauthorized access") -> None:
        super().__init__(message, status_code=401)
