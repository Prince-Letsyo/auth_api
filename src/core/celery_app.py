from celery import Celery  # pyright: ignore[reportMissingTypeStubs]

from src.config import config
from src.core.env import env

broker_url = env.celery_broker_url or "celery://guest:guest@localhost:5672//"

celery_app = Celery(
    "auth_api_worker",
    broker=broker_url,
    backend=env.redis.url or "redis://localhost", 
    include=[
        "src.tasks.email_task",
    ],
)

celery_app.conf.update(  # pyright: ignore[reportUnknownMemberType]
    # === Result backend (optional, can still be Redis) ===
    redis_backend_use_ssl=False if config.env.env_mode != "production" else True,
    redis_max_connections=20,
    result_backend_transport_options={
        "global_keyprefix": "auth_api:celery:",  # ← prefix all keys
        "visibility_timeout": 3600,
    },
    task_ignore_result=True,  # ← No task results stored
    task_store_errors_even_if_ignored=True,  # ← BUT keep errors! (for monitoring)
    result_expires=3600,
    # === Reliability settings (CRUCIAL with RabbitMQ) ===
    task_acks_late=True,  # worker acknowledges AFTER task success
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # no prefetch → exactly-once capable
    # === Queues & routing ===
    task_default_queue="auth_app.default",
    task_create_missing_queues=True,
    task_queues={
        "auth_app.default": {
            "exchange": "auth_app.default",
            "routing_key": "auth_app.default",
        },
        "auth_app.priority.high": {
            "exchange": "auth_app.priority.high",
            "routing_key": "auth_app.priority.high",
            "queue_arguments": {"x-max-priority": 10},
        },
        "auth_app.priority.low": {
            "exchange": "auth_app.priority.low",
            "routing_key": "auth_app.priority.low",
        },
    },
    task_routes={
        "src.tasks.email_task.send_*": {"queue": "auth_app.priority.high"},
    },
    task_acks_on_failure_or_timeout=False,
    worker_pool="solo",
    broker_connection_retry_on_startup=True,
    # Optional: also silence the old deprecated setting (just in case)
    broker_connection_retry=False,
)

