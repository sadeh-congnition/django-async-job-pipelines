import pytest

from que.jobs import job, run_job, lock_new_job_for_running
from que.models import JobDBModel, LockedJob


@job(name="name")
def func(a, b):
    """
    function implementation
    """
    print("In func")
    print(a, b)


@job(name="name2")
def funcs():
    """
    function implementation
    """


def test_run_job_blocking(db):
    func("a", b="b")
    assert JobDBModel.objects.count() == 0


def test_run_job_blocking_with_bad_function_args(db):
    with pytest.raises(TypeError):
        func("a", "c", b="b")


def test_create_job_background(db):
    func.run_later("a", "b", "c", d="d")
    assert JobDBModel.objects.count() == 1

    j = JobDBModel.objects.first()
    assert j.name == func.name
    assert j.args_and_kwargs == {"args": ["a", "b", "c"], "kwargs": {"d": "d"}}, (
        j.args_and_kwargs
    )
    assert j.status == JobDBModel.Status.NEW


def test_run_job_background_with_bad_function_args(db):
    j = func.run_later("a", "b", "c", d="d")
    run_job(j)

    j = JobDBModel.objects.first()
    assert j.status == JobDBModel.Status.ERROR, j.status
    assert "TypeError" in j.error


def test_run_job_background_with_good_function_args(db):
    j = func.run_later("a", b="b")
    run_job(j)
    j = JobDBModel.objects.first()
    assert j.status == JobDBModel.Status.DONE, j.error
    assert not j.error


def test_lock_new_job_for_running(db):
    func.run_later("a", b="b")
    job, _ = lock_new_job_for_running()

    assert LockedJob.is_locked(job.id)

    run_job(job)

    assert LockedJob.objects.count() == 0


def test_lock_same_job_multiple_times_fails(db):
    func.run_later("a", b="b")
    _, _ = lock_new_job_for_running()
    j, l = lock_new_job_for_running()

    assert j is None
    assert l is None
