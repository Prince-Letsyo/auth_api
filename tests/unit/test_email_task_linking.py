from src.modules.auth.router import fire_and_forget
from src.tasks.email import log_task_failure


class FakeSignature:
    def __init__(self):
        self.called_with = None

    def apply_async(self, **kwargs):
        self.called_with = kwargs
        return "ok"


def test_fire_and_forget_links_success_and_error():
    sig = FakeSignature()
    result = fire_and_forget(sig, 1, key="value")
    assert result == "ok"
    assert sig.called_with is not None
    assert "link" in sig.called_with
    assert "link_error" in sig.called_with


def test_log_task_failure_accepts_extra_args():
    # Should not raise when extra args are passed by Celery.
    log_task_failure(
        task_id="task-123",
        exc=RuntimeError("boom"),
        traceback="trace",
        einfo="einfo",
        extra="value",
    )
