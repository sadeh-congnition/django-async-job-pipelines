import djclick as click
import random
from time import sleep
from django.conf import settings
from rich import print
import concurrent.futures

from que.models import JobDBModel
from que.jobs import lock_new_job_for_running, run_job

from blah.js import func  # this registers job


@click.command()
def command():
    try:
        conf = settings.DJJP
        concurrency_type = conf.get("concurrency", "threads")
        if concurrency_type not in ("threads", "asyncio"):
            raise ValueError(
                f"Invalid concurrency type: {concurrency_type}. Valid values are 'asyncio' and 'threads'!"
            )
        concurrency_limit = conf.get("concurrency_limit", 10)

        if concurrency_type == "threads":
            run_threads(int(concurrency_limit))
    except AttributeError:
        run_default()


def run_threads(max_threads: int):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(run_default): i for i in range(max_threads)}
        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print("[red]Ooops[/red]", e)
            else:
                print(f"[green]Future number {futures[f]} completed![/green]")

    print("[green]All threads exited!")


def run_default():
    speel_choices = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
    while True:
        job, lock = lock_new_job_for_running()

        if not job:
            choice = random.choice(speel_choices)
            sleep(choice)
            print("[cyan]Going to sleep:[/cyan]", choice)
            if not JobDBModel.objects.filter(status=JobDBModel.Status.NEW).exists():
                break
            continue

        run_job(job)

        lock.delete()

        if not JobDBModel.objects.filter(status=JobDBModel.Status.NEW).exists():
            num_in_progress_jobs = JobDBModel.objects.filter(
                status=JobDBModel.Status.IN_PROGRESS
            ).count()
            print(
                "[orange]Number of in progress jobs is [/orange]", num_in_progress_jobs
            )
            break

    print("[yellow]No more jobs, exiting[/yellow]")
