from django.db import models


class JobDBModel(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW"
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

    class Meta:
        db_table = "djjp_job"


class LockedJob(models.Model):
    job_id = models.BigAutoField(primary_key=True)

    class Meta:
        db_table = "djjp_locked_job"

    @classmethod
    def is_locked(cls, job_id: int):
        return cls.objects.filter(job_id=job_id).exists()
