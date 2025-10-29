from dataclasses import dataclass
from django.conf import settings


@dataclass
class Config:
    concurrency: str = "threads"
    concurrency_limit: int = 10  # max number of concurrent threads or `asyncio` tasks
    db_name: str = "default"
    scheduler_interval: int = 5 * 60  # seconds
    stuck_jobs_requeue_interval: int = 60  # seconds

    def __post_init__(self):
        try:
            django_conf = settings.DJJP
        except AttributeError:
            return

        concurrency_type = django_conf.get("concurrency", self.concurrency)
        if concurrency_type not in ("threads", "asyncio"):
            raise ValueError(
                f"Invalid concurrency type: {concurrency_type}. Valid values are 'asyncio' and 'threads'!"
            )
        self.concurrency = concurrency_type

        concurrency_limit = django_conf.get("concurrency_limit", self.concurrency_limit)
        self.concurrency_limit = int(concurrency_limit)

        db_name = django_conf.get("db_name", self.db_name)
        if db_name not in settings.DATABASES:
            raise ValueError(
                f"Invalid db name: {db_name}. Valid values are {settings.DATABASES.keys()}!"
            )
        self.db_name = db_name

        scheduler_interval = django_conf.get(
            "scheduler_interval", self.scheduler_interval
        )
        self.scheduler_interval = int(scheduler_interval)

        stuck_jobs_requeue_interval = django_conf.get(
            "stuck_jobs_requeue_interval", self.stuck_jobs_requeue_interval
        )
        self.stuck_jobs_requeue_interval = int(stuck_jobs_requeue_interval)


config = Config()
