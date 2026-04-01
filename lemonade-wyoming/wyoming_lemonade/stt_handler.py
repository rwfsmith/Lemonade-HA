"""Wyoming Speech-to-Text handler — bridges to Lemonade's Whisper API."""

from __future__ import annotations

import asyncio
import io
import logging
import wave
from typing import Any

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler

from .const import WHISPER_CHANNELS, WHISPER_SAMPLE_RATE, WHISPER_SAMPLE_WIDTH
from .lemonade_client import LemonadeClient

_LOGGER = logging.getLogger(__name__)


class LemonadeSttHandler(AsyncEventHandler):
    """Handle one STT client connection.

    Event flow (client → server):
        Describe  →  Info (with AsrProgram)
        Transcribe → (stored)
        AudioStart → (init buffer)
        AudioChunk → (accumulate)
        AudioStop  → transcribe via Lemonade → Transcript  (then disconnect)
    """

    # How long to wait for Lemonade setup before giving up on a request
    _READY_TIMEOUT = 600.0

    def __init__(
        self,
        wyoming_info: Info,
        client: LemonadeClient,
        stt_model: str,
        stt_language: str,
        stt_beam_size: int,
        ready_event: asyncio.Event,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._info_event = wyoming_info.event()
        self._client = client
        self._model = stt_model
        self._language = stt_language
        self._beam_size = stt_beam_size
        self._ready_event = ready_event

        # Per-request state
        self._audio_buf = b""
        self._rate = WHISPER_SAMPLE_RATE
        self._width = WHISPER_SAMPLE_WIDTH
        self._channels = WHISPER_CHANNELS

    async def handle_event(self, event: Event) -> bool:  # noqa: D401
        if Describe.is_type(event.type):
            await self.write_event(self._info_event)
            _LOGGER.debug("Responded to Describe")
            return True

        if Transcribe.is_type(event.type):
            transcribe = Transcribe.from_event(event)
            if transcribe.language:
                self._language = transcribe.language
            _LOGGER.debug("Transcribe request — language=%s", self._language)
            return True

        if AudioStart.is_type(event.type):
            audio_start = AudioStart.from_event(event)
            self._rate = audio_start.rate
            self._width = audio_start.width
            self._channels = audio_start.channels
            self._audio_buf = b""
            _LOGGER.debug(
                "AudioStart — rate=%d width=%d channels=%d",
                self._rate,
                self._width,
                self._channels,
            )
            return True

        if AudioChunk.is_type(event.type):
            chunk = AudioChunk.from_event(event)
            self._audio_buf += chunk.audio
            return True

        if AudioStop.is_type(event.type):
            if not self._ready_event.is_set():
                _LOGGER.info("Waiting for Lemonade setup to complete before transcribing …")
                try:
                    await asyncio.wait_for(
                        self._ready_event.wait(), timeout=self._READY_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    _LOGGER.error("Timed out waiting for Lemonade — dropping STT request")
                    await self.write_event(Transcript(text="").event())
                    return False

            _LOGGER.debug(
                "AudioStop — total bytes=%d  (%.1f s)",
                len(self._audio_buf),
                len(self._audio_buf)
                / (self._rate * self._width * self._channels),
            )
            wav_bytes = self._pcm_to_wav(
                self._audio_buf, self._rate, self._width, self._channels
            )
            try:
                text = await self._client.transcribe(
                    wav_bytes,
                    model=self._model,
                    language=self._language,
                )
            except Exception:
                _LOGGER.exception("Transcription failed")
                text = ""

            _LOGGER.info("Transcript: %s", text)
            await self.write_event(
                Transcript(text=text).event()
            )
            # Disconnect after responding (standard Wyoming STT pattern)
            return False

        return True

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _pcm_to_wav(
        pcm: bytes, rate: int, width: int, channels: int
    ) -> bytes:
        """Wrap raw PCM bytes in a WAV container."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(width)
            wf.setframerate(rate)
            wf.writeframes(pcm)
        return buf.getvalue()
