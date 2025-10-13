from que.jobs import job, run_job
from time import sleep
from rich import print
import random


@job(name="name")
def func(a, b):
    choices = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1]
    """
    function implementation
    """
    choice = random.choice(choices)
    sleep(choice)
    print("[yellow]Slept: [/yellow]", choice)
