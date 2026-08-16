import asyncio
import math
from collections import defaultdict, deque
from time import monotonic


class InMemoryRateLimiter:
    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, client_id: str, *, limit: int) -> tuple[bool, int, int]:
        now = monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            requests = self._requests[client_id]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= limit:
                retry_after = max(1, math.ceil(self.window_seconds - (now - requests[0])))
                return False, retry_after, 0
            requests.append(now)
            return True, 0, limit - len(requests)
