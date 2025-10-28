from django.db import models
import uuid


class Manager(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    updated_at = models.DateTimeField(auto_now=True)


class JobDBModel(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW"
        BLOCKED = "BLOCKED"
        IN_PROGRESS = "IN_PROGRESS"
        DONE = "DONE"
        ERROR = "ERROR"

    name = models.CharField(max_length=255)
    args_and_kwargs = models.JSONField()
    error = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=255, choices=Status.choices, default=Status.NEW
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    next_step = models.UUIDField(null=True, blank=True)
    step = models.UUIDField(null=True, blank=True)
    manager = models.ForeignKey(
        Manager, blank=True, null=True, on_delete=models.DO_NOTHING
    )

    class Meta:
        db_table = "djjp_job"

    def __str__(self) -> str:
        return f"{self.id}, {self.name}, {self.status}"


class LockedJob(models.Model):
    job = models.OneToOneField(JobDBModel, on_delete=models.CASCADE, primary_key=True)

    class Meta:
        db_table = "djjp_locked_job"

    @classmethod
    def is_locked(cls, job: JobDBModel):
        return cls.objects.filter(job=job).exists()


class ScheduledJob(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    job_name = models.CharField(max_length=255)
    interval = models.JSONField()
    run_ts = models.DateTimeField(null=True, blank=True)
