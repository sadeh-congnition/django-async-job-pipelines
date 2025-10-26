from uuid import UUID, uuid4

from django_async_job_pipelines.models import JobDBModel
from django_async_job_pipelines.db_layer import db


class Step:
    def __init__(self):
        self.id: UUID = uuid4()
        self.jobs: list[JobDBModel] = []
        self.next_step: Step | None = None
        self.prev_step: Step | None = None

    def add_job(self, job, *args, **kwargs) -> JobDBModel:
        if self.prev_step:
            j = job.run_later_block(*args, step_id=self.id, **kwargs)
            self.jobs.append(j)
            return j
        else:
            j = job.run_later(*args, step_id=self.id, **kwargs)
            self.jobs.append(j)
            return j

    def create_next_step(self) -> "Step":
        self.next_step = Step()
        self.next_step.prev_step = self

        for j in self.jobs:
            db.add_next_id_to_job(j, self.next_step.id)

        return self.next_step
