from typing import Tuple
from uuid import UUID
from contextvars import ContextVar
from asgiref.sync import async_to_sync
import inspect
from dataclasses import dataclass
from django.db.utils import IntegrityError
import traceback
from typing import Callable

from django_async_job_pipelines.models import JobDBModel, LockedJob
from django_async_job_pipelines.db_layer import db
from .logger import logger

djjp_currently_running_job = ContextVar("djjp_currently_running_job")


@dataclass
class Job:
    name: str
    timeout: int
    func_to_run: Callable | None = None

    def __call__(self, *args, **kwargs):
        assert self.func_to_run
        if inspect.iscoroutinefunction(self.func_to_run):
            async_to_sync(self.func_to_run)(*args, **kwargs)
        else:
            self.func_to_run(*args, **kwargs)

    def run_later(self, *args, step_id: UUID | None = None, **kwargs) -> JobDBModel:
        return db.run_later(
            *args, job_name=self.name, timeout=self.timeout, step_id=step_id, **kwargs
        )

    async def arun_later(
        self, *args, step_id: UUID | None = None, **kwargs
    ) -> JobDBModel:
        res = await db.arun_later(
            *args, job_name=self.name, timeout=self.timeout, step_id=step_id, **kwargs
        )
        return res

    def run_later_block(
        self, *args, step_id: UUID | None = None, **kwargs
    ) -> JobDBModel:
        return db.run_later_block(
            *args, job_name=self.name, timeout=self.timeout, step_id=step_id, **kwargs
        )


@dataclass
class Registry:
    jobs: dict[str, Job] | None = None

    def add(self, job: Job):
        if not self.jobs:
            self.jobs = {}

        if job.name in self.jobs:
            raise ValueError(
                f"Job with name {job.name} already exists, job names must be unique!"
            )

        self.jobs[job.name] = job

    def find_job(self, name: str) -> Job:
        assert self.jobs, "Registry is empty! No jobs were registered!"
        if name not in self.jobs:
            error = f"Job with name {name} does not exist in the registry!"
            error += " Maybe you changed the name of an already queued job?"
            raise ValueError(error)
        return self.jobs[name]


job_registry = Registry()


def job(*args, **kwargs):
    if "name" not in kwargs:
        raise ValueError("Job must have a name!")
    if "timeout" not in kwargs:
        raise ValueError("Job must have a timeout!")

    job_obj = Job(name=kwargs["name"], timeout=kwargs["timeout"])
    job_registry.add(job_obj)

    def inner(func):
        job_obj.func_to_run = func
        return job_obj

    return inner


def run_job(job: JobDBModel, lock: LockedJob | None = None) -> bool:
    try:
        djjp_currently_running_job.set(job)
        if job.status != JobDBModel.Status.NEW:
            raise ValueError("Job is not in NEW status!")

        res = db.mark_as_in_progress(job)
        if not res:
            logger.debug(f"Could not mark job as in progress: {job.id}")
            return False

        j = job_registry.find_job(job.name)

        if job.args_and_kwargs:
            args = job.args_and_kwargs["args"]
            kwargs = job.args_and_kwargs["kwargs"]
        else:
            args = []
            kwargs = {}

        j(*args, **kwargs)

    except Exception:
        db.mark_as_error(job, traceback.format_exc())
    else:
        db.mark_next_step_jobs_as_new(job)
        db.mark_as_done(job)
    finally:
        if lock:
            db.delete_lock(lock)
        return True


def lock_new_job_for_running() -> Tuple[JobDBModel | None, LockedJob | None]:
    try:
        job, lock = db.lock_one()
        return job, lock
    except IntegrityError:
        logger.exception("Lock IntegrityError")
        return None, None
