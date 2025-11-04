import random
from time import sleep
from .logger import logger


def retry_exponentially(
    exception_type, initial_delay=0.1, max_delay=5.0, num_retries: int = 10, jitter=True
):
    def decorator(func_decorated):
        def wrapper(*args, **kwargs):
            current_retry = 0
            while current_retry < num_retries:
                try:
                    return func_decorated(*args, **kwargs)
                except exception_type as e:
                    current_retry += 1
                    if current_retry >= num_retries:
                        raise e  # Re-raise the last exception if all retries fail

                    delay = initial_delay * (2 ** (current_retry - 1))
                    if jitter:
                        delay = min(
                            delay + random.uniform(0, delay * 0.1), max_delay
                        )  # Add up to 10% random jitter, capped at max_delay
                    else:
                        delay = min(delay, max_delay)

                    logger.info(
                        f"Invoking {func_decorated.__name__} attempt {current_retry}/{num_retries} failed. Retrying in {delay} seconds."
                    )
                    sleep(delay)

        return wrapper

    return decorator
