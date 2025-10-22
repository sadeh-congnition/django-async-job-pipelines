# djjp

The simplest job queue ever:

- No extra dependencies: use your existing db or sqlite
- Create background jobs (`async` or regular) from any number of processes
- Run multiple consumers as separate processes
- Configure concurrency - via multithreading - for each consumer
- Monitor jobs via a Django admin page

Coming soon:

- `asyncio` based concurrency
- Pipelines as chain of jobs
- Dedicated db as job queue (using Django's multi db support)
- HTTP interface for the job queue
- Scheduled jobs
- Remove `rich` package dependency
- Remove `djclick` package dependency

The project's Kanban board is [here](https://github.com/orgs/sadeh-congnition/projects/2/views/1).

## Setup

### Install the Package

pypi package coming soon...

### Add to Django Apps

```Python
INSTALLED_APPS = [
    ...,
    'django_async_job_pipelines',
]
```

### Run Database Migrations

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
def func(a, b):
    """
    function implementation
    """
```

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

### async Jobs

`async` and regular jobs and mixing them is supported.

However, depending on the type of concurrency you've configured this app with

- If the majority of your jobs are `async` then use the `asyncio` concurrency type. (coming soon!)
- Otherwise use the 'threads' concurrency type.

For advanced users, note the following scenarios can occur:

- Concurrency type is `asyncio` but the job is a regular Python function
- Concurrency type is `threads` but the job is an `async` function

In such cases, `sync_to_async` and `async_to_sync` functions of the `asgi` package are used to resolve the mismatch by changing the flavor of the function. If you're using `async` jobs to improve performance you want to pay attention to such mismatches.

### Choosing the Database Engine

If the load on this db is too high and you want to offload the job queue traffic to another database, then either create a PR or wait a bit until this feature is added.

By default, Django uses sqlite3 as db. When using this option keep in mind that sqlite3 data is in one file. It's your responsibility to ensure this file is backed up and things like server restarts don't lead to loss of all data in that file.

## Benchmark

Setup: Mac mini 2025, M4, Python 3.13.5

Task: time.sleep between 0.01 to 0.1 seconds.

## Creating/Consuming Jobs One by One

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
