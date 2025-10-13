# djjp

The simplest job queue ever:

- No extra dependencies: use your existing db or sqlite
- Create background jobs from any number of processes
- Run multiple consumers as separate processes
- Configure concurrency - via multithreading - for each consumer
- Monitor jobs via a Django admin page

Coming soon:

- Support for async jobs
- Support for multiple consumers via asyncio workers
- Support for using a dedicated db as the job queue (using Django's multi db support)
- Exposing the job queue via a HTTP interface

## Setup

### Install the Package

pypi package coming soon...

### Add Django Dependencies

```Python
INSTALLED_APPS = [
    ...,
    'django-async-job-pipelines',
]

```

### Configure

In your Django `settings` module:

```Python
DJJP = {
    "concurrency": "threads",
    "concurrency_limit": 50,
}
```

## Create Background Jobs

```python

from django_async_job_pipelines.jobs import job

@job(name="name")  # Must be unique
def func(a, b):
    """
    function implementation
    """

### Run the Consumer
The consumer is a Django management command:
```bash
python manage.py start_consumer
```

## Benchmark

Setup: Mac mini 2025, M4, 24 GB, Python 3.13.5

Task: sleep between 0.01 to 0.1 seconds.

## Creating/Consuming Jobs One by One

| No. of Jobs | Creation | Consumption | No. Threads | No. asyncio Tasks | DB Engine |
| ----------- | -------- | ----------- | ----------- | ----------------- | ------ |
| 100 | < 1s | 6s | 1 | - | Sqlite3 |
| 1,000 | < 1s | < 1s | 1 | - | Sqlite3 |
| 10,000 | 2s | 11m7s | 1 | - | Sqlite3 |
| 100 | < 1s | 3s | 5 | - | Sqlite3 |
| 1,000 | < 1s | 19s | 10 | - | Sqlite3 |
| 1,000 | < 1s | 7s | 20 | - | Sqlite3 |
| 1,000 | < 1s | 4s | 50 | - | Sqlite3 |
| 10,000 | 2s | 2m51s | 50 | - | Sqlite3 |
