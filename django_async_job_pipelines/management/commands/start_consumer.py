import djclick as click

from django_async_job_pipelines.consumers import run_threads
from django_async_job_pipelines.config import Config


@click.command()
def command():
    config = Config()
    if config.concurrency == "threads":
        run_threads(config.concurrency_limit)
    else:
        raise NotImplementedError("asyncio concurrency not implemented yet!")
