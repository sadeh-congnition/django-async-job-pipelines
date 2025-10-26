from dataclasses import dataclass
from django.utils import timezone
from datetime import datetime
from uuid import UUID, uuid4
from django_async_job_pipelines.models import (
    JobDBModel,
    LockedJob,
    Manager,
    ScheduledJob,
)
from django.conf import settings


manager_id = uuid4()


@dataclass
class DefaultDB:
    name: str

    def new_job_exists(self) -> bool:
        return JobDBModel.objects.filter(status=JobDBModel.Status.NEW).exists()

    def run_later(
        self, *args, job_name: str, step_id: UUID | None, **kwargs
    ) -> JobDBModel:
        return JobDBModel.objects.create(
            name=job_name,
            args_and_kwargs={"args": args, "kwargs": kwargs},
            step=step_id,
        )

    def run_later_block(
        self, *args, job_name: str, step_id: UUID | None, **kwargs
    ) -> JobDBModel:
        return JobDBModel.objects.create(
            name=job_name,
            args_and_kwargs={"args": args, "kwargs": kwargs},
            status=JobDBModel.Status.BLOCKED,
            step=step_id,
        )

    def lock_one(self):
        j = JobDBModel.objects.filter(
            status=JobDBModel.Status.NEW, lockedjob__isnull=True
        ).first()
        if not j:
            return None, None

        lock = LockedJob.objects.create(job=j)
        manager, _ = Manager.objects.get_or_create(id=manager_id)
        j.manager = manager
        j.save()
        return j, lock

    def mark_as_in_progress(self, job: JobDBModel):
        job.status = job.Status.IN_PROGRESS
        job.save()

    def mark_as_done(self, job: JobDBModel):
        job.status = job.Status.DONE
        job.save()

    def mark_as_error(self, job: JobDBModel, error: str):
        job.status = job.Status.ERROR
        job.error = error
        job.save()

    def delete_lock(self, lock: LockedJob):
        lock.delete()

    def add_next_id_to_job(self, job: JobDBModel, next_step_id: UUID):
        job.next_step = next_step_id
        job.save()

    def mark_next_step_jobs_as_new(self, job: JobDBModel):
        JobDBModel.objects.filter(step=job.next_step).update(
            status=JobDBModel.Status.NEW
        )

    def create_or_update_schedule(
        self, name: str, job_name: str, interval: dict, first_run_ts: datetime
    ) -> ScheduledJob:
        schedj, _ = ScheduledJob.objects.update_or_create(
            name=name,
            defaults={
                "job_name": job_name,
                "interval": interval,
                "run_ts": first_run_ts,
            },
        )
        return schedj

    def get_all_scheduled_jobs(self):
        return ScheduledJob.objects.all()

    def delete_scheduled_job(self, sched_job: ScheduledJob):
        sched_job.delete()

    def all_scheduled_job(self):
        return ScheduledJob.objects.all()

    def update_run_ts_to_now(self, sched_job: ScheduledJob):
        sched_job.run_ts = timezone.now()
        sched_job.save()

    def lock_job_by_id(self, job_id: UUID):
        j = JobDBModel.objects.get(id=job_id)
        lock = LockedJob.objects.create(job=j)
        manager, _ = Manager.objects.get_or_create(id=manager_id)
        j.manager = manager
        j.save()
        return j, lock


@dataclass
class CustomDB:
    name: str

    def new_job_exists(self) -> bool:
        return (
            JobDBModel.objects.filter(status=JobDBModel.Status.NEW)
            .using(self.name)
            .exists()
        )

    def run_later(self, *args, job_name: str, step_id: UUID | None, **kwargs):
        return JobDBModel.objects.using(self.name).create(
            name=job_name,
            args_and_kwargs={"args": args, "kwargs": kwargs},
            step=step_id,
        )

    def run_later_block(self, *args, job_name: str, step_id: UUID | None, **kwargs):
        return JobDBModel.objects.using(self.name).create(
            step=step_id,
            name=job_name,
            args_and_kwargs={"args": args, "kwargs": kwargs},
            status=JobDBModel.Status.BLOCKED,
        )

    def lock_one(self):
        j = (
            JobDBModel.objects.using(self.name)
            .filter(status=JobDBModel.Status.NEW, lockedjob__isnull=True)
            .first()
        )
        if not j:
            return None, None

        lock = LockedJob.objects.using(self.name).create(job=j)
        manager, _ = Manager.objects.using(self.name).get_or_create(id=manager_id)
        j.manager = manager
        j.save(using=self.name)
        return j, lock

    def mark_as_in_progress(self, job: JobDBModel):
        job.status = job.Status.IN_PROGRESS
        job.save(using=self.name)

    def mark_as_done(self, job: JobDBModel):
        job.status = job.Status.DONE
        job.save(using=self.name)

    def mark_as_error(self, job: JobDBModel, error: str):
        job.status = job.Status.ERROR
        job.error = error
        job.save(using=self.name)

    def delete_lock(self, lock: LockedJob):
        lock.delete(using=self.name)

    def add_next_id_to_job(self, job: JobDBModel, next_step_id: UUID):
        job.next_step = next_step_id
        job.save(using=self.name)

    def mark_next_step_jobs_as_new(self, job: JobDBModel):
        JobDBModel.objects.using(self.name).filter(step=job.next_step).update(
            status=JobDBModel.Status.NEW
        )

    def create_or_update_schedule(
        self, name: str, job_name: str, interval: dict, first_run_ts: datetime
    ) -> ScheduledJob:
        # TODO: catch IntegrityError
        sched_job, _ = ScheduledJob.objects.using(self.name).update_or_create(
            name=name,
            defaults={
                "job_name": job_name,
                "interval": interval,
                ", run_ts": first_run_ts,
            },
        )
        return sched_job

    def get_all_scheduled_jobs(self):
        return ScheduledJob.objects.using(self.name).all()

    def delete_scheduled_job(self, sched_job: ScheduledJob):
        sched_job.delete(using=self.name)

    def update_run_ts_to_now(self, sched_job: ScheduledJob):
        sched_job.run_ts = timezone.now()
        sched_job.save(using=self.name)

    def all_scheduled_job(self):
        return ScheduledJob.objects.using(self.name).all()

    def lock_job_by_id(self, job_id: UUID):
        j = JobDBModel.objects.using(self.name).get(id=job_id)
        lock = LockedJob.objects.using(self.name).create(job=j)
        manager, _ = Manager.objects.using(self.name).get_or_create(id=manager_id)
        j.manager = manager
        j.save(using=self.name)
        return j, lock


@dataclass
class DB:
    implementation: CustomDB | DefaultDB | None = None

    def create(self, name: str):
        if name == "default":
            self.implementation = DefaultDB(name)
        else:
            self.implementation = CustomDB(name)

    def new_job_exists(self) -> bool:
        assert self.implementation
        return self.implementation.new_job_exists()

    def run_later(
        self, *args, job_name: str, step_id: UUID | None, **kwargs
    ) -> JobDBModel:
        assert self.implementation
        return self.implementation.run_later(
            *args, job_name=job_name, step_id=step_id, **kwargs
        )

    def run_later_block(
        self, *args, job_name: str, step_id: UUID | None, **kwargs
    ) -> JobDBModel:
        assert self.implementation
        return self.implementation.run_later_block(
            *args, job_name=job_name, step_id=step_id, **kwargs
        )

    def lock_one(self):
        assert self.implementation
        return self.implementation.lock_one()

    def mark_as_in_progress(self, job: JobDBModel):
        assert self.implementation
        self.implementation.mark_as_in_progress(job)

    def mark_as_done(self, job: JobDBModel):
        assert self.implementation
        self.implementation.mark_as_done(job)

    def mark_as_error(self, job: JobDBModel, error: str):
        assert self.implementation
        self.implementation.mark_as_error(job, error)

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

    def all_scheduled_job(self):
        assert self.implementation
        return self.implementation.all_scheduled_job()

    def lock_job_by_id(self, job_id: UUID):
        assert self.implementation
        return self.implementation.lock_job_by_id(job_id)


conf = settings.DJJP
db = DB()
db_name = conf.get("db_name", "default")
if db_name not in settings.DATABASES:
    raise ValueError(
        f"Invalid db name: {db_name}. Valid values are {settings.DATABASES.keys()}!"
    )
db.create(db_name)
print(f"Database name is: {db_name}")
