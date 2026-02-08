if __name__ == "__main__":
    import uvicorn

    from src.config import config
    from src.app import app

    uvicorn.run(
        "src.app:app",
        host=config.env.host,
        port=config.env.port,
        reload=config.env.reload,
        log_level=config.env.log_level,
    )
