import threading
import signal
import traceback
import random
from time import sleep
from django_async_job_pipelines.jobs import lock_new_job_for_running, run_job
import concurrent.futures
from django_async_job_pipelines.db_layer import db
from django_async_job_pipelines.scheduler import (
    get_scheduled_jobs_to_run,
    run_scheduled_job,
)
from .logger import logger

exit_event = threading.Event()


def run_threads(max_threads: int):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads + 2) as executor:
        futures = {executor.submit(run_default, i): i for i in range(max_threads)}
        futures[executor.submit(run_manager_thread, "manager_thread")] = (
            "manager_thread"
        )
        futures[executor.submit(run_scheduler_thread, "scheduler_thread")] = (
            "scheduler_thread"
        )

        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
            except Exception:
                e = traceback.format_exc()
                logger.exception(e)
            else:
                logger.info(f"Future {futures[f]} completed!")

    logger.info("All threads exited!")


def run_default(thread_number: int):
    sleep_choices = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
    while True:
        job, lock = lock_new_job_for_running()

        if not job:
            choice = random.choice(sleep_choices)
            sleep(choice)
            logger.debug(f"Worker threat {thread_number} going to sleep: {choice}")
            if exit_event.is_set():
                logger.info(f"Thread number {thread_number} exiting")
                break
            continue

        res = run_job(job, lock)
        if res:
            logger.debug(f"Ran job with id {job.id}")

        if exit_event.is_set():
            logger.info(f"Thread number {thread_number} exiting")
            break


def run_manager_thread(name: str):
    while True:
        logger.info(f"Manager thread running: {name}")
        db.send_manager_beat()
        sleep(5)
        if exit_event.is_set():
            logger.info(f"Manager thread exiting: {name}")
            break


def run_scheduler_thread(name: str):
    while True:
        logger.debug(f"Scheduler thread running: {name}")
        for sched_job in get_scheduled_jobs_to_run():
            try:
                run_scheduled_job(sched_job)
            except Exception:
                logger.exception("Error while running scheduled job")
        sleep(10)
        if exit_event.is_set():
            logger.info(f"Scheduler thread exiting: {name}")
            break


def signal_handler(signum, frame):
    exit_event.set()


signal.signal(signal.SIGINT, signal_handler)
