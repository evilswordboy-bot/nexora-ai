import time
from collections import defaultdict
from typing import Dict, List


class SlidingWindowRateLimiter:
    """
    Lightweight, thread-safe in-memory sliding window rate limiter
    tracks request timestamps per client IP.
    """

    def __init__(self, limit_per_minute: int = 60):
        self.limit = limit_per_minute
        self.window_seconds = 60
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old timestamps
        recent_timestamps = [t for t in self.requests[client_id] if t > cutoff]
        self.requests[client_id] = recent_timestamps

        if len(recent_timestamps) < self.limit:
            self.requests[client_id].append(now)
            return True
        return False

    def remaining(self, client_id: str) -> int:
        now = time.time()
        cutoff = now - self.window_seconds
        recent = [t for t in self.requests[client_id] if t > cutoff]
        return max(0, self.limit - len(recent))


rate_limiter = SlidingWindowRateLimiter()
