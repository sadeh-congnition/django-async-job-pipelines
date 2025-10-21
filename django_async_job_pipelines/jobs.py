from typing import Tuple
from asgiref.sync import async_to_sync
import inspect
from dataclasses import dataclass
from django.db.utils import IntegrityError
import traceback
from typing import Callable

from .models import JobDBModel, LockedJob


@dataclass
class Job:
    name: str
    func_to_run: Callable | None = None

    def __call__(self, *args, **kwargs):
        assert self.func_to_run
        if inspect.iscoroutinefunction(self.func_to_run):
            async_to_sync(self.func_to_run)(*args, **kwargs)
        else:
            self.func_to_run(*args, **kwargs)

    def run_later(self, *args, **kwargs):
        return JobDBModel.make_new(self.name, *args, **kwargs)


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
    job_obj = Job(name=kwargs["name"])
    job_registry.add(job_obj)

    def inner(func):
        job_obj.func_to_run = func
        return job_obj

    return inner


def run_job(job: JobDBModel, lock: LockedJob | None = None):
    job.mark_as_in_progress()

    try:
        j = job_registry.find_job(job.name)

        if job.args_and_kwargs:
            args = job.args_and_kwargs["args"]
            kwargs = job.args_and_kwargs["kwargs"]
        else:
            args = []
            kwargs = {}

        j(*args, **kwargs)

    except Exception:
        job.mark_as_error(traceback.format_exc())
    else:
        job.mark_as_done()
    finally:
        if lock:
            lock.delete()


def lock_new_job_for_running() -> Tuple[JobDBModel | None, LockedJob | None]:
    try:
        job, lock = JobDBModel.lock_one()
        return job, lock
    except IntegrityError:
        return None, None
