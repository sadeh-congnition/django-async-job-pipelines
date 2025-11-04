from dataclasses import dataclass
from django.db.models import F
from datetime import datetime, timedelta
from django.utils import timezone
from uuid import UUID, uuid4
from django.db.utils import OperationalError
from django_async_job_pipelines.models import (
    JobDBModel,
    LockedJob,
    Manager,
    ScheduledJob,
)
from django_async_job_pipelines.logger import logger
from django_async_job_pipelines.config import config
from django_async_job_pipelines.utils import retry_exponentially

manager_id = uuid4()


@dataclass
class CustomDB:
    name: str

    @retry_exponentially(OperationalError)
    def new_job_exists(self) -> bool:
        res = (
            JobDBModel.objects.filter(status=JobDBModel.Status.NEW)
            .using(self.name)
            .exists()
        )
        logger.debug(f"{res}")
        return res

    @retry_exponentially(OperationalError)
    def run_later(
        self, *args, job_name: str, timeout: int, step_id: UUID | None, **kwargs
    ):
        res = JobDBModel.objects.using(self.name).create(
            name=job_name,
            args_and_kwargs={"args": args, "kwargs": kwargs},
            step=step_id,
            timeout=timeout,
        )
        logger.debug(f"{res.id}")
        return res

    @retry_exponentially(OperationalError)
    def run_later_block(
        self, *args, job_name: str, timeout: int, step_id: UUID | None, **kwargs
    ):
        res = JobDBModel.objects.using(self.name).create(
            step=step_id,
            name=job_name,
            args_and_kwargs={"args": args, "kwargs": kwargs},
            status=JobDBModel.Status.BLOCKED,
            timeout=timeout,
        )
        logger.debug(f"{res.id}")
        return res

    @retry_exponentially(OperationalError)
    def get_or_create_manager(self):
        manager, created = Manager.objects.using(self.name).get_or_create(id=manager_id)
        logger.debug(f"{manager}, {created}")
        return manager

    def lock_one(self):
        j = self.get_new_job_without_lock()
        # TODO get job first, then update using its ID and version or counter field(new column)
        if not j:
            return None, None

        lock = self.create_lock_for_job(j)
        manager = self.get_or_create_manager()

        @retry_exponentially(OperationalError)
        def save_job():
            j.manager = manager
            j.save(using=self.name, update_fields=["manager"])

        save_job()
        logger.debug(f"Saved manager on job: {j.id}")
        return j, lock

    @retry_exponentially(OperationalError)
    def get_new_job_without_lock(self):
        res = (
            JobDBModel.objects.using(self.name)
            .filter(status=JobDBModel.Status.NEW, lockedjob__isnull=True)
            .order_by("?")
            .first()
        )
        if res:
            logger.debug(f"Job without lock {res.id} status; {res.status}")
        if not res:
            logger.debug("No jobs found!")
        return res

    @retry_exponentially(OperationalError)
    def create_lock_for_job(self, job: JobDBModel):
        res = LockedJob.objects.using(self.name).create(job=job)
        logger.debug(f"{job.id}")
        return res

    @retry_exponentially(OperationalError)
    def mark_as_in_progress(self, job: JobDBModel) -> bool:
        j = JobDBModel.objects.using(self.name).get(id=job.id)
        logger.debug(f"Job {j.id} before marking as in prgoress: {j.status}")
        rows_updated = (
            JobDBModel.objects.using(self.name)
            .filter(id=job.id, status=JobDBModel.Status.NEW)
            .update(
                status=JobDBModel.Status.IN_PROGRESS,
                should_run_by=timezone.now() + timedelta(seconds=job.timeout),
            )
        )
        logger.debug(
            f"Marked job as in progress:{job.id} Num rows updated: {rows_updated}"
        )
        if int(rows_updated) == 1:
            return True
        return False

    def mark_as_new(self, job: JobDBModel, message):
        if job.messages is None:
            job.messages = [message.to_dict()]
        else:
            job.messages.append(message.to_dict())
        job.status = JobDBModel.Status.NEW
        job.manager = None
        job.should_run_by = None

        @retry_exponentially(OperationalError)
        def save_job():
            job.save(
                using=self.name,
                update_fields=["messages", "status", "manager", "should_run_by"],
            )

        save_job()
        logger.debug(f"Marked job as NEW: {job.id}")
        self.delete_job_lock(job)

    @retry_exponentially(OperationalError)
    def mark_as_done(self, job: JobDBModel) -> bool:
        rows_updated = (
            JobDBModel.objects.using(self.name)
            .filter(id=job.id, status=JobDBModel.Status.IN_PROGRESS)
            .update(status=JobDBModel.Status.DONE)
        )
        logger.debug(f"Marked job as done: {job.id} Rows udpated: {rows_updated}")
        j = JobDBModel.objects.using(self.name).get(id=job.id)
        logger.debug(f"Job {j.id} after marking as done: {j.status}")
        if int(rows_updated) == 1:
            return True
        return False

    @retry_exponentially(OperationalError)
    def mark_as_error(self, job: JobDBModel, error: str) -> bool:
        logger.debug(f"Marking job as error: {job.id} Error: {error}")
        j = JobDBModel.objects.using(self.name).get(id=job.id)
        logger.debug(f"Job {j.id} before marking as error: {j.status}")
        rows_updated = (
            JobDBModel.objects.using(self.name)
            .filter(status=JobDBModel.Status.IN_PROGRESS)
            .update(status=JobDBModel.Status.ERROR, error=error)
        )
        logger.debug(f"{job.id}: {rows_updated}")
        if rows_updated == 1:
            return True
        return False

    @retry_exponentially(OperationalError)
    def delete_lock(self, lock: LockedJob):
        logger.debug(f"{lock.job.id}")
        lock.delete(using=self.name)

    @retry_exponentially(OperationalError)
    def delete_job_lock(self, job: JobDBModel):
        res = LockedJob.objects.using(self.name).filter(job=job).delete()
        logger.debug(f"{res}")
        return res

    @retry_exponentially(OperationalError)
    def add_next_id_to_job(self, job: JobDBModel, next_step_id: UUID):
        job.next_step = next_step_id
        job.save(using=self.name, update_fields=["next_step"])
        logger.debug(f"{job.id}")

    @retry_exponentially(OperationalError)
    def mark_next_step_jobs_as_new(self, job: JobDBModel):
        JobDBModel.objects.using(self.name).filter(step=job.next_step).update(
            status=JobDBModel.Status.NEW
        )
        logger.debug(f"{job.id}")

    @retry_exponentially(OperationalError)
    def create_or_update_schedule(
        self, name: str, job_name: str, interval: dict, first_run_ts: datetime
    ) -> ScheduledJob:
        # TODO: catch IntegrityError
        sched_job, created = ScheduledJob.objects.using(self.name).update_or_create(
            name=name,
            defaults={
                "job_name": job_name,
                "interval": interval,
                "run_ts": first_run_ts,
            },
        )
        logger.debug(f"{sched_job}, {created}")
        return sched_job

    @retry_exponentially(OperationalError)
    def get_all_scheduled_jobs(self):
        res = ScheduledJob.objects.using(self.name).all()
        logger.debug(f"{[r for r in res]}")
        return res

    @retry_exponentially(OperationalError)
    def delete_scheduled_job(self, sched_job: ScheduledJob):
        sched_job.delete(using=self.name)
        logger.debug(f"{sched_job.id}")

    @retry_exponentially(OperationalError)
    def update_run_ts_to_now(self, sched_job: ScheduledJob):
        sched_job.run_ts = timezone.now()
        sched_job.save(using=self.name, update_fields=["run_ts"])
        logger.debug(f"{sched_job.id}")

    def lock_job_by_id(self, job_id: UUID):
        j = self.get_job_by_id(job_id)
        lock = self.create_lock_for_job(j)
        manager, _ = self.get_or_create_manager()

        @retry_exponentially(OperationalError)
        def save_job():
            j.manager = manager
            j.save(using=self.name, update_fields=["manager"])

        save_job()
        logger.debug(f"Set manager for job: {j.id}")
        return j, lock

    @retry_exponentially(OperationalError)
    def get_job_by_id(self, job_id: UUID):
        res = JobDBModel.objects.using(self.name).get(id=job_id)
        logger.debug(f"{res}")
        return res

    @retry_exponentially(OperationalError)
    def send_manager_beat(self):
        Manager.objects.using(self.name).update_or_create(
            id=manager_id, defaults={"updated_at": timezone.now()}
        )
        logger.debug(f"{manager_id}")

    @retry_exponentially(OperationalError)
    def update_manager_beat(self, ts):
        Manager.objects.using(self.name).filter(id=manager_id).update(updated_at=ts)
        logger.debug(f"{manager_id}")

    @retry_exponentially(OperationalError)
    def get_stale_managers(self, cut_off_seconds: int):
        res = Manager.objects.filter(
            updated_at__lt=timezone.now() - timedelta(seconds=cut_off_seconds)
        )
        logger.debug(f"{[r.id for r in res]}")
        return res

    @retry_exponentially(OperationalError)
    def get_timed_out_jobs(self):
        res = JobDBModel.objects.using(self.name).filter(
            status__in=[JobDBModel.Status.IN_PROGRESS],
            should_run_by__lt=timezone.now(),
        )
        logger.debug(f"{[r.id for r in res]}")
        return res


@dataclass
class DB:
    implementation: CustomDB | None = None

    def create(self, name: str):
        self.implementation = CustomDB(name)

    def new_job_exists(self) -> bool:
        assert self.implementation
        return self.implementation.new_job_exists()

    def run_later(
        self, *args, job_name: str, timeout: int, step_id: UUID | None, **kwargs
    ) -> JobDBModel:
        assert self.implementation
        return self.implementation.run_later(
            *args, job_name=job_name, timeout=timeout, step_id=step_id, **kwargs
        )

    def run_later_block(
        self, *args, job_name: str, timeout: int, step_id: UUID | None, **kwargs
    ) -> JobDBModel:
        assert self.implementation
        return self.implementation.run_later_block(
            *args, job_name=job_name, timeout=timeout, step_id=step_id, **kwargs
        )

    def lock_one(self):
        assert self.implementation
        return self.implementation.lock_one()

    def mark_as_in_progress(self, job: JobDBModel) -> bool:
        assert self.implementation
        return self.implementation.mark_as_in_progress(job)

    def mark_as_done(self, job: JobDBModel) -> bool:
        assert self.implementation
        return self.implementation.mark_as_done(job)

    def mark_as_error(self, job: JobDBModel, error: str) -> bool:
        assert self.implementation
        return self.implementation.mark_as_error(job, error)

    def delete_lock(self, lock: LockedJob):
        assert self.implementation
        self.implementation.delete_lock(lock)

    def add_next_id_to_job(self, job: JobDBModel, next_step_id: UUID):
        assert self.implementation
        self.implementation.add_next_id_to_job(job, next_step_id)

    def mark_next_step_jobs_as_new(self, job: JobDBModel):
        assert self.implementation
        if job.next_step is None:
            return
        self.implementation.mark_next_step_jobs_as_new(job)

    def create_or_update_schedule(
        self, name: str, job_name: str, interval: dict, first_run_ts: datetime
    ) -> ScheduledJob:
        assert self.implementation
        return self.implementation.create_or_update_schedule(
            name, job_name, interval, first_run_ts
        )

    def get_all_scheduled_jobs(self):
        assert self.implementation
        return self.implementation.get_all_scheduled_jobs()

    def delete_scheduled_job(self, sched_job: ScheduledJob):
        assert self.implementation
        return self.implementation.delete_scheduled_job(sched_job)

    def update_run_ts_to_now(self, sched_job: ScheduledJob):
        assert self.implementation
        self.implementation.update_run_ts_to_now(sched_job)

    def lock_job_by_id(self, job_id: UUID):
        assert self.implementation
        return self.implementation.lock_job_by_id(job_id)

    def send_manager_beat(self):
        assert self.implementation
        return self.implementation.send_manager_beat()

    def get_or_create_manager(self):
        assert self.implementation
        return self.implementation.get_or_create_manager()

    def update_manager_beat(self, ts):
        assert self.implementation
        return self.implementation.update_manager_beat(ts)

    def get_stale_managers(self, cut_off_seconds: int):
        assert self.implementation
        return self.implementation.get_stale_managers(cut_off_seconds)

    def get_timed_out_jobs(self):
        assert self.implementation
        return self.implementation.get_timed_out_jobs()

    def mark_as_new(self, job: JobDBModel, message):
        assert self.implementation
        return self.implementation.mark_as_new(job, message)


db = DB()
db.create(config.db_name)
logger.info(f"Database name is: {config.db_name}")
