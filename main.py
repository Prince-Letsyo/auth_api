if __name__ == "__main__":
    import uvicorn

    from src.config import config

    uvicorn.run(
        config.env.app,
        host=config.env.host,
        port=config.env.port,
        reload=config.env.reload,
        log_level=config.env.log_level,
    )
