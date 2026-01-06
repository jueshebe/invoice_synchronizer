"""Rate limit Module."""

import time
from threading import Lock
import logging


class RateLimiter:
    """Rate limiter class"""

    def __init__(self, max_requests_per_minute: int, logger: logging.Logger):
        self.max_requests_per_minute = max_requests_per_minute
        self.min_interval = 60.0 / max_requests_per_minute  # segundos entre requests
        self.last_request_time = 0.0
        self.lock = Lock()
        self.logger = logger

    def wait_if_needed(self) -> None:
        """Wait the necessary time to respect the rate limit."""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                self.logger.debug(f"Rate limit: esperando {sleep_time:.2f} segundos")
                time.sleep(sleep_time)

            self.last_request_time = time.time()
