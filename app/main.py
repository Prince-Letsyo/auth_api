from fastapi import FastAPI

from app.config import config

app = FastAPI(
    title=config.app_name,
)


@app.get("/")
def index():
    return {"message": "Welcome to Authentication Api Project!"}
