from dataclasses import dataclass
import djclick as click
from django.conf import settings

from django_async_job_pipelines.consumers import run_threads


@dataclass
class Config:
    concurrency: str = "threads"
    concurrency_limit: int = 10


@click.command()
def command():
    default_config = Config()
    try:
        conf = settings.DJJP
        concurrency_type = conf.get("concurrency", default_config.concurrency)
        if concurrency_type not in ("threads", "asyncio"):
            raise ValueError(
                f"Invalid concurrency type: {concurrency_type}. Valid values are 'asyncio' and 'threads'!"
            )
        concurrency_limit = conf.get(
            "concurrency_limit", default_config.concurrency_limit
        )

        if concurrency_type == "threads":
            run_threads(int(concurrency_limit))
        else:
            raise NotImplementedError("asyncio concurrency not implemented yet!")

    except AttributeError:  # config not set in `settings.py` of `django`
        run_threads(default_config.concurrency_limit)
