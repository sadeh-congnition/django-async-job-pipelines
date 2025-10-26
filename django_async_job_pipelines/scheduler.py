from dataclasses import dataclass, field
from django.db.utils import IntegrityError
from datetime import timedelta
from django.utils import timezone
from django_async_job_pipelines.db_layer import db
from .jobs import Job, job_registry, lock_new_job_for_running, run_job
from .models import ScheduledJob


class Every:
    def __init__(self):
        self.interval = {"type": "every"}

    def seconds(self, seconds: int):
        self.interval["seconds"] = seconds
        return self

    def to_dict(self):
        return self.interval

    @property
    def interval_seconds(self) -> int:
        return self.interval["seconds"]


@dataclass
class Registry:
    jobs: list[ScheduledJob] = field(default_factory=list)

    def job_names(self) -> set[str]:
        return {j.name for j in self.jobs}

    def add(self, job: ScheduledJob):
        self.jobs.append(job)

    def clear(self):
        self.jobs = list()


registry = Registry()


class Scheduler:
    def add(
        self, name: str, job: Job, interval: Every, trigger_first_run_now: bool = False
    ):
        if name in registry.job_names():
            raise ValueError(f"Schedule with name {name} already exists!")

        if not isinstance(job, Job):
            raise TypeError("Job must be an instance of Job!")

        if job.name not in job_registry.jobs:
            raise ValueError(f"Job with name {name} does not exist!")

        first_run_ts = timezone.now()
        if trigger_first_run_now:
            first_run_ts = timezone.now() - timedelta(
                seconds=interval.interval_seconds + 60
            )

        sched_job = db.create_or_update_schedule(
            name, job.name, interval.to_dict(), first_run_ts
        )
        registry.add(sched_job)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sync_with_db()

    def sync_with_db(self):
        for sched_job_db_model in db.get_all_scheduled_jobs():
            if sched_job_db_model.name not in registry.job_names():
                db.delete_scheduled_job(sched_job_db_model)


def get_scheduled_jobs_to_run():
    for sched_job in db.all_scheduled_job()
        seconds = sched_job.interval["seconds"]
        if sched_job.run_ts < timezone.now() - timedelta(seconds=seconds):
            yield sched_job


def run_scheduled_job(sched_job: ScheduledJob):
    j = job_registry.find_job(sched_job.job_name)
    job_db_model = j.run_later()
    try:
        job, lock = db.lock_job_by_id(job_db_model.id)
    except IntegrityError:
        print("[red]Lock IntegrityError while locking scheduled job![/red]")
        return
    run_job(job, lock)
    db.update_run_ts_to_now(sched_job)
