from dataclasses import dataclass
from django_async_job_pipelines.models import JobDBModel, LockedJob
from django.conf import settings


@dataclass
class DefaultDB:
    name: str

    def new_job_exists(self) -> bool:
        return JobDBModel.objects.filter(status=JobDBModel.Status.NEW).exists()

    def run_later(self, *args, job_name: str, **kwargs):
        return JobDBModel.objects.create(
            name=job_name, args_and_kwargs={"args": args, "kwargs": kwargs}
        )

    def lock_one(self):
        j = JobDBModel.objects.filter(status=JobDBModel.Status.NEW).first()
        if not j:
            return None, None

        lock = LockedJob.objects.create(job_id=j.id)
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


@dataclass
class CustomDB:
    name: str

    def new_job_exists(self) -> bool:
        return (
            JobDBModel.objects.filter(status=JobDBModel.Status.NEW)
            .using(self.name)
            .exists()
        )

    def run_later(self, *args, job_name: str, **kwargs):
        return JobDBModel.objects.using(self.name).create(
            name=job_name, args_and_kwargs={"args": args, "kwargs": kwargs}
        )

    def lock_one(self):
        j = (
            JobDBModel.objects.using(self.name)
            .filter(status=JobDBModel.Status.NEW)
            .first()
        )
        if not j:
            return None, None

        lock = LockedJob.objects.using(self.name).create(job_id=j.id)
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

    def run_later(self, *args, job_name: str, **kwargs):
        assert self.implementation
        return self.implementation.run_later(*args, job_name=job_name, **kwargs)

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


conf = settings.DJJP
db = DB()
db_name = conf.get("db_name", "default")
if db_name not in settings.DATABASES:
    raise ValueError(
        f"Invalid db name: {db_name}. Valid values are {settings.DATABASES.keys()}!"
    )
db.create(db_name)
print(f"Database name is: {db_name}")
