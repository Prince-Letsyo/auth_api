from celery import chain  # pyright: ignore[reportMissingTypeStubs]
from src.tasks.email_task import log_task_failure

def fire_and_forget(*tasks):  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
    """Fire Celery chain with automatic success/error logging"""
    workflow = chain(*tasks)  # pyright: ignore[reportUnknownArgumentType]
    workflow.link_error(log_task_failure.s())  # pyright: ignore[reportCallIssue, reportUnknownMemberType]
    workflow.apply_async()  # pyright: ignore[reportUnknownMemberType, reportUnusedCallResult]