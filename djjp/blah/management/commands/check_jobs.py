import djclick as click
from rich import print

from que.models import JobDBModel, LockedJob


@click.command()
@click.argument("num-done", type=int)
@click.argument("num-error", type=int, default=0)
def command(num_done: int, num_error: int):
    actually_done = JobDBModel.objects.filter(status=JobDBModel.Status.DONE).count()
    new_count = JobDBModel.objects.filter(status=JobDBModel.Status.NEW).count()
    error_count = JobDBModel.objects.filter(status=JobDBModel.Status.ERROR).count()
    first = JobDBModel.objects.first()

    assert actually_done == num_done, actually_done
    print(f"[green]Checked {num_done} background jobs are DONE in db[/green]")

    assert error_count == num_error, error_count
    print(f"[green]Checked {num_error} background jobs are ERROR in db[/green]")

    assert LockedJob.objects.count() == 0, LockedJob.objects.count()
    print("[green]Checked there are no locked jobs in db[/green]")
