"""Asynchronous-friendly audio transcription boundary for the prototype."""

from dataclasses import dataclass
from typing import Protocol


class AudioTranscriber(Protocol):
    def transcribe(self, content: bytes) -> str:
        """Return a transcript or raise an explicit processing error."""


@dataclass(frozen=True)
class TranscriptAudioTranscriber:
    """Controlled adapter used until a hosted speech provider is configured."""

    transcript: str

    def transcribe(self, content: bytes) -> str:
        if not content:
            raise ValueError("audio must not be empty.")
        if not self.transcript.strip():
            raise RuntimeError("audio transcription is not configured.")
        return self.transcript.strip()
