from django.contrib import admin


from .models import JobDBModel, LockedJob


@admin.register(JobDBModel)
class JobDBModelAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "created_at", "updated_at")


@admin.register(LockedJob)
class LockedJobAdmin(admin.ModelAdmin):
    list_display = ("job_id",)


# Register your models here.
