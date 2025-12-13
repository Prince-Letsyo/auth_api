from fastapi import FastAPI
from src.auth.router import auth_router


def register_api_routes(app: FastAPI, path: str="/api") -> None:
    app.include_router(auth_router, prefix=path)  