from typing import Any, override
from fastapi.routing import APIRouter

from src.core.router.errors import ErrorResponse, ValidationErrorResponse


ID_LIST=["{id}", "{slug}", "{uuid}"]

class CustomRouter(APIRouter):
    @override
    def add_api_route(
        self,
        *args,  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
        **kwargs,  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
    ) -> None:
        path = args[0] if args else kwargs.get("path", "")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        dependencies = kwargs.get("dependencies") or [] # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        
        # Define default error responses
        default_responses: dict[int, dict[str, Any | str]] = {  # pyright: ignore[reportExplicitAny]
            422: {
                "model": ValidationErrorResponse,
                "description": "Validation error",
            },
            500: {
                "model": ErrorResponse,
                "description": "Internal server error",
            },
        }
        
        # Add 401 automatically if auth-related dependencies exist
        if any(
            getattr(dep.dependency, "__name__", "").lower()  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            in {"require_auth", "get_current_user", "authenticate_user", "auth"}
            for dep in dependencies  # pyright: ignore[reportUnknownVariableType]
            if hasattr(dep, "dependency")  # pyright: ignore[reportUnknownArgumentType]
        ):
            default_responses[401] = {
                "model": ErrorResponse,
                "description": "Unauthorized access",
            }

        # Add 404 automatically if path looks like a resource identifier
        if "{" in path and any(x in path for x in ID_LIST):
            default_responses[404] = {
                "model": ErrorResponse,
                "description": "Resource not found",
            }

        # Extract and normalize responses
        responses: dict[str, Any] | None = kwargs.pop("responses", None)  # pyright: ignore[reportUnknownMemberType, reportExplicitAny, reportUnknownVariableType]
        if responses is None:
            responses = {}


        # Call FastAPI’s original method
        super().add_api_route(
            *args,  # pyright: ignore[reportUnknownArgumentType]
            responses={**default_responses, **responses},
            **kwargs,
        )
