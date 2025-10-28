import sys
import threading
import signal
import traceback
import random
from time import sleep
from rich import print
from django_async_job_pipelines.jobs import lock_new_job_for_running, run_job
import concurrent.futures
from django_async_job_pipelines.db_layer import db

exit_event = threading.Event()


def run_threads(max_threads: int):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads + 1) as executor:
        futures = {executor.submit(run_default, i): i for i in range(max_threads)}
        futures[executor.submit(run_manager_thread, "manager_thread")] = (
            "manager_thread"
        )
        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
            except Exception:
                e = traceback.format_exc()
                print("[red]Ooops[/red]", e)
            else:
                print(f"[green]Future number {futures[f]} completed![/green]")

    print("[green]All threads exited!")


def run_default(thread_number: int):
    sleep_choices = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
    while True:
        job, lock = lock_new_job_for_running()

        if not job:
            choice = random.choice(sleep_choices)
            sleep(choice)
            print(f"[cyan]Worker threat {thread_number} going to sleep:[/cyan]", choice)
            if exit_event.is_set():
                print(f"[red]Thread number {thread_number} exiting[/red]")
                break
            continue

        run_job(job, lock)
        print(f"Ran job with id {job.id}")

        # this is for debugging only
        # if not JobDBModel.objects.filter(status=JobDBModel.Status.NEW).exists():
        #     num_in_progress_jobs = JobDBModel.objects.filter(
        #         status=JobDBModel.Status.IN_PROGRESS
        #     ).count()
        #     print(
        #         "[orange]Number of in progress jobs is [/orange]", num_in_progress_jobs
        #     )
        #     break
        if exit_event.is_set():
            print(f"[red]Thread number {thread_number} exiting[/red]")
            break


def run_manager_thread(name: str):
    while True:
        print("[yellow]Manager thread runing[/yellow]")
        db.send_manager_beat()
        sleep(5)
        if exit_event.is_set():
            print("[red]Manager thread exiting[/red]")
            break

    sys.exit()


def signal_handler(signum, frame):
    exit_event.set()


signal.signal(signal.SIGINT, signal_handler)
