# djjp - django-async-job-pipelines

The simplest job queue ever:

- No extra dependencies: use your existing db or sqlite
- Create background jobs (`async` or regular) from any number of processes
- Run multiple consumers as separate processes
- Configure concurrency - via multithreading - for each consumer
- Monitor jobs via a Django admin page
- Debug failed jobs using their error stacktrace

Coming soon:

- `asyncio` based concurrency
- Pipelines as chain of jobs
- HTTP interface for the job queue
- Scheduled jobs
- Remove `rich` package dependency
- Remove `djclick` package dependency

Progress on features is tracked on the [Kanban board](https://github.com/orgs/sadeh-congnition/projects/2/views/1).

Full documentation is [here](https://github.com/sadeh-congnition/django-async-job-pipelines/wiki).

## How to Use

### Install

```bash
pip install https://github.com/sadeh-congnition/django-async-job-pipelines.git
```

A `pypi` package is coming soon once the job scheduler and `SIGINT` signal handler are implemented.

### Setup

Add `django_async_job_pipelines` to `Django` installed apps in your `settings.py`:

```Python
INSTALLED_APPS = [
    ...,
    'django_async_job_pipelines',
]
```

Run Database Migrations:

```bash
python manage.py migrate
```

### Configure

Configuration is optional. In your Django `settings` module:

```Python
DJJP = {
    "concurrency": "threads",  # ['threads', 'asyncio'] are valid values, `asyncio` not implemented yet
    "concurrency_limit": 10,  # how many jobs to run concurrently per process
    "db_name": "default",
}
```

The above is the default configuration.

### Create Background Jobs

```python
from django_async_job_pipelines.jobs import job

@job(name="name")  # Job names must be unique
def job1(a, b):
    """
    function implementation
    """

job1.run_later("a", b="b")
```

Jobs functions are identified by their `name` which you pass to the `job` decorator.
So, you an change the implementation of the `job1` function even after you've pushed jobs to the queue.

### Run the Consumer

Create a [new Django management command](https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/#module-django.core.management). Load your jobs modules and call the `start_consumer` command. In the below example I'm creating a command called `run_consumer` in `run_consumer.py`:

```python
from django.core.management.base import BaseCommand
from django.core.management import call_command

from blah.jobs import job1  # import job functions so they get registered


class Command(BaseCommand):
    def handle(self, *args, **options):
        call_command("start_consumer")
```

Then, run the command you just created:

```bash
python manage.py run_consumer
```

## Benchmark

Setup: Mac mini 2025 with M4 chip, Python 3.13.5

Task: `time.sleep` between 0.01 to 0.1 seconds.

### Creating/Consuming Jobs One by One

| No. of Jobs | Creation | Consumption | No. Threads | No. `asyncio` Tasks | DB Engine |
| ----------- | -------- | ----------- | ----------- | ----------------- | ------ |
| 100 | < 1s | 6s | 1 | - | Sqlite3 |
| 1,000 | < 1s | < 1m6s | 1 | - | Sqlite3 |
| 10,000 | 2s | 11m7s | 1 | - | Sqlite3 |
| 100 | < 1s | 3s | 5 | - | Sqlite3 |
| 1,000 | < 1s | 19s | 10 | - | Sqlite3 |
| 1,000 | < 1s | 7s | 20 | - | Sqlite3 |
| 1,000 | < 1s | 4s | 50 | - | Sqlite3 |
| 10,000 | 2s | 2m51s | 50 | - | Sqlite3 |
