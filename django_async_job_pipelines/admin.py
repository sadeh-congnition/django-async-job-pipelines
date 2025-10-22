from django.contrib import admin


from django_async_job_pipelines.db_layer import db
from .models import JobDBModel, LockedJob


class MultiDBModelAdmin(admin.ModelAdmin):
    assert db.implementation
    using = db.implementation.name

    def save_model(self, request, obj, form, change):
        # Tell Django to save objects to the 'other' database.
        obj.save(using=self.using)

    def delete_model(self, request, obj):
        # Tell Django to delete objects from the 'other' database
        obj.delete(using=self.using)

    def get_queryset(self, request):
        # Tell Django to look for objects on the 'other' database.
        return super().get_queryset(request).using(self.using)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Tell Django to populate ForeignKey widgets using a query
        # on the 'other' database.
        return super().formfield_for_foreignkey(
            db_field, request, using=self.using, **kwargs
        )


@admin.register(JobDBModel)
class JobDBModelAdmin(MultiDBModelAdmin):
    list_display = ("id", "name", "status", "created_at", "updated_at")


@admin.register(LockedJob)
class LockedJobAdmin(MultiDBModelAdmin):
    list_display = ("job_id",)
