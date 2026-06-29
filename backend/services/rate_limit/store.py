import time
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    window_seconds: int
    remaining: int
    retry_after_seconds: int


@dataclass
class _CounterState:
    count: int
    window_ends_at: float


class InMemoryRateLimitStore:
    def __init__(
        self,
        *,
        cleanup_interval_seconds: int = 60,
        max_keys: int = 20000,
    ) -> None:
        self._lock = Lock()
        self._counters: dict[str, _CounterState] = {}
        self._cleanup_interval_seconds = max(1, cleanup_interval_seconds)
        self._max_keys = max(100, max_keys)
        self._last_cleanup_at = 0.0

    def _cleanup_expired_locked(self, now: float) -> None:
        expired_keys = [
            key
            for key, state in self._counters.items()
            if now >= state.window_ends_at
        ]
        for key in expired_keys:
            self._counters.pop(key, None)
        self._last_cleanup_at = now

    def _evict_until_under_limit_locked(self) -> None:
        while len(self._counters) >= self._max_keys:
            oldest_key = min(
                self._counters.keys(),
                key=lambda existing_key: self._counters[existing_key].window_ends_at,
            )
            self._counters.pop(oldest_key, None)

    def consume(self, *, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = time.time()
        retry_after_seconds = 0

        with self._lock:
            if now - self._last_cleanup_at >= self._cleanup_interval_seconds:
                self._cleanup_expired_locked(now)

            if key not in self._counters and len(self._counters) >= self._max_keys:
                self._cleanup_expired_locked(now)
                if len(self._counters) >= self._max_keys:
                    self._evict_until_under_limit_locked()

            state = self._counters.get(key)
            if state is None or now >= state.window_ends_at:
                state = _CounterState(count=0, window_ends_at=now + window_seconds)
                self._counters[key] = state

            if state.count >= limit:
                retry_after_seconds = max(1, int(state.window_ends_at - now))
                return RateLimitDecision(
                    allowed=False,
                    limit=limit,
                    window_seconds=window_seconds,
                    remaining=0,
                    retry_after_seconds=retry_after_seconds,
                )

            state.count += 1
            remaining = max(0, limit - state.count)
            return RateLimitDecision(
                allowed=True,
                limit=limit,
                window_seconds=window_seconds,
                remaining=remaining,
                retry_after_seconds=retry_after_seconds,
            )
