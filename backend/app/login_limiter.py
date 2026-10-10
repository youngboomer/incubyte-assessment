import math
from collections.abc import Callable


class LoginLimiter:
    def __init__(
        self, max_attempts: int, window_seconds: int, clock: Callable[[], float]
    ) -> None:
        self._max = max_attempts
        self._window = window_seconds
        self._clock = clock
        self._failures: dict[str, list[float]] = {}

    def _recent(self, client: str) -> list[float]:
        cutoff = self._clock() - self._window
        recent = [t for t in self._failures.get(client, []) if t > cutoff]
        if recent:
            self._failures[client] = recent
        else:
            self._failures.pop(client, None)
        return recent

    def retry_after(self, client: str) -> int | None:
        recent = self._recent(client)
        if len(recent) < self._max:
            return None
        return max(1, math.ceil(recent[0] + self._window - self._clock()))

    def record_failure(self, client: str) -> None:
        self._failures.setdefault(client, []).append(self._clock())

    def clear(self, client: str) -> None:
        self._failures.pop(client, None)
