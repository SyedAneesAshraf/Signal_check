"""Application component readiness state."""

from dataclasses import dataclass
from threading import Lock


@dataclass
class Readiness:
    index_loaded: bool = False
    embedding_model_loaded: bool = False
    nli_model_loaded: bool = False
    last_error: str | None = None


class ReadinessState:
    def __init__(self) -> None:
        self._state = Readiness()
        self._lock = Lock()

    def snapshot(self) -> Readiness:
        with self._lock:
            return Readiness(**self._state.__dict__)

    def mark_ready(self) -> None:
        with self._lock:
            self._state.index_loaded = True
            self._state.embedding_model_loaded = True
            self._state.nli_model_loaded = True
            self._state.last_error = None

    def mark_error(self, message: str) -> None:
        with self._lock:
            self._state.last_error = message


readiness = ReadinessState()
