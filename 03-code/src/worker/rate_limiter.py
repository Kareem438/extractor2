"""
Rate Limit Handler

Handles Claude API rate limiting with automatic recovery.
Pauses processing when rate limited and resumes automatically.
"""

import time
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import text
from src.database.connection import engine
from anthropic import RateLimitError
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Handles rate limiting for Claude API calls"""

    def __init__(
        self,
        worker_id: str,
        check_interval_seconds: int = 60,
        initial_backoff_seconds: int = 300
    ):
        """
        Initialize rate limiter.

        Args:
            worker_id: Worker ID for status updates
            check_interval_seconds: Seconds between rate limit checks
            initial_backoff_seconds: Initial backoff when rate limited
        """
        self.worker_id = worker_id
        self.check_interval_seconds = check_interval_seconds
        self.initial_backoff_seconds = initial_backoff_seconds
        self.is_rate_limited = False
        self.rate_limited_until: Optional[datetime] = None

    def handle_rate_limit(self, error: RateLimitError):
        """
        Handle a rate limit error.

        Updates worker status and enters waiting mode.

        Args:
            error: The rate limit error from Claude API
        """
        self.is_rate_limited = True
        self.rate_limited_until = datetime.now() + timedelta(
            seconds=self.initial_backoff_seconds
        )

        logger.warning(
            f"Rate limit detected. Pausing until "
            f"{self.rate_limited_until.isoformat()}"
        )

        # Update worker status in database
        self._update_worker_status(
            status="rate_limited",
            rate_limited_until=self.rate_limited_until,
            last_error=str(error)
        )

    def wait_for_rate_limit_clear(self, test_api_func) -> bool:
        """
        Wait for rate limit to clear by periodically testing API.

        Args:
            test_api_func: Function to test API connection (returns bool)

        Returns:
            True when rate limit is cleared
        """
        logger.info(
            f"Entering rate limit wait loop. "
            f"Will check every {self.check_interval_seconds}s"
        )

        while self.is_rate_limited:
            # Wait for check interval
            time.sleep(self.check_interval_seconds)

            # Update heartbeat
            self._update_heartbeat()

            # Test if rate limit cleared
            logger.info("Testing if rate limit cleared...")

            try:
                if test_api_func():
                    # Rate limit cleared!
                    self._clear_rate_limit()
                    return True

            except RateLimitError:
                # Still rate limited
                logger.info("Still rate limited, continuing to wait...")
                continue

            except Exception as e:
                # Other error - log but continue waiting
                logger.error(f"Error during rate limit test: {e}")
                continue

        return True

    def _clear_rate_limit(self):
        """Clear rate limit state and update worker status"""
        self.is_rate_limited = False
        self.rate_limited_until = None

        logger.info("Rate limit cleared! Resuming processing.")

        self._update_worker_status(
            status="running",
            rate_limited_until=None,
            last_error=None
        )

    def _update_worker_status(
        self,
        status: str,
        rate_limited_until: Optional[datetime] = None,
        last_error: Optional[str] = None
    ):
        """
        Update worker status in database.

        Args:
            status: Worker status
            rate_limited_until: When rate limit expires
            last_error: Error message
        """
        sql = text("""
        UPDATE worker_status
        SET status = :status,
            rate_limited_until = :rate_limited_until,
            last_error = :last_error,
            updated_at = NOW()
        WHERE worker_id = :worker_id
        """)

        with engine.connect() as conn:
            conn.execute(sql, {
                "worker_id": self.worker_id,
                "status": status,
                "rate_limited_until": rate_limited_until,
                "last_error": last_error
            })
            conn.commit()

    def _update_heartbeat(self):
        """Update worker heartbeat timestamp"""
        sql = text("""
        UPDATE worker_status
        SET last_heartbeat = NOW(),
            updated_at = NOW()
        WHERE worker_id = :worker_id
        """)

        with engine.connect() as conn:
            conn.execute(sql, {"worker_id": self.worker_id})
            conn.commit()

    def check_rate_limit_status(self) -> bool:
        """
        Check if currently rate limited.

        Returns:
            True if rate limited
        """
        return self.is_rate_limited

    def get_time_until_clear(self) -> Optional[int]:
        """
        Get seconds until rate limit should clear.

        Returns:
            Seconds until clear, or None if not rate limited
        """
        if not self.is_rate_limited or not self.rate_limited_until:
            return None

        delta = self.rate_limited_until - datetime.now()
        return max(0, int(delta.total_seconds()))
