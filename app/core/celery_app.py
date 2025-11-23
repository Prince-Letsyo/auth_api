from celery import Celery  # pyright: ignore[reportMissingTypeStubs]

from app.core.env import env

broker_url = env.CELERY_BROKER_URL

celery_app = Celery("worker", broker=broker_url)

celery_app.conf.update(  # pyright: ignore[reportUnknownMemberType]
    # === Result backend (optional, can still be Redis) ===
    result_backend=env.REDIS_URL,  # or rpc://, db+sqlite:// etc.
    # === Reliability settings (CRUCIAL with RabbitMQ) ===
    task_acks_late=True,  # worker acknowledges AFTER task success
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # no prefetch → exactly-once capable
    # === Queues & routing ===
    task_default_queue="celery",
    task_queues={
        "celery": {"exchange": "celery", "routing_key": "celery"},
        "high_priority": {
            "exchange": "celery",
            "routing_key": "high_priority",
            "queue_arguments": {"x-max-priority": 10},
        },
    },
    task_routes={
        "app.tasks.email.send_welcome_email": {"queue": "high_priority"},
    },
    task_acks_on_failure_or_timeout=False,
)
