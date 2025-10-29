from django.utils import timezone
from rich import print
from datetime import datetime
from django_async_job_pipelines.jobs import job
from django_async_job_pipelines.db_layer import db
from dataclasses import dataclass


@dataclass
class TimedOutMsg:
    timestamp: datetime
    type: str = "status change"
    reason: str = "job timed out"
    details: dict | None = None

    def __post_init__(self):
        self.details = {"old_status": "IN_PROGRESS", "new_status": "NEW"}

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "type": self.type,
            "reason": self.reason,
            "details": self.details,
        }


@job(name="requeue_timed_out_jobs", timeout=60)
def requeue_timed_out_jobs():
    print("[orange]Requeue stuck jobs  scheduled job running[/orange]")
    for j in db.get_timed_out_jobs():
        db.mark_as_new(j, TimedOutMsg(timestamp=timezone.now()))
