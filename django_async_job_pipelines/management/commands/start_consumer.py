import djclick as click

from django_async_job_pipelines.consumers import run_threads
from django_async_job_pipelines.config import config
from django_async_job_pipelines.scheduler import Scheduler, Every
from django_async_job_pipelines.default_jobs import requeue_timed_out_jobs


@click.command()
def command():
    stuck_jobs_requeue_interval = config.stuck_jobs_requeue_interval
    with Scheduler() as sched:
        sched.add(
            name="reset_stuck_jobs_schedule",
            job=requeue_timed_out_jobs,
            interval=Every().seconds(stuck_jobs_requeue_interval),
        )

    if config.concurrency == "threads":
        run_threads(config.concurrency_limit)
    else:
        raise NotImplementedError("asyncio concurrency not implemented yet!")
