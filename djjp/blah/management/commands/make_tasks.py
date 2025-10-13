import djclick as click
from rich import print

from que.jobs import job
from que.models import JobDBModel
from blah.js import func


@click.command()
@click.argument("num_jobs")
def command(num_jobs: int):
    JobDBModel.objects.all().delete()

    num_jobs = int(num_jobs)
    for i in range(num_jobs):
        func.run_later("a", b="b")

    assert JobDBModel.objects.count() == num_jobs

    print(f"[green]Created {num_jobs} background jobs in db[/green]")
