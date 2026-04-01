"""Wyoming Text-to-Speech handler — bridges to Lemonade's Kokoro API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler
from wyoming.tts import Synthesize

from .const import KOKORO_CHANNELS, KOKORO_SAMPLE_RATE, KOKORO_SAMPLE_WIDTH
from .lemonade_client import LemonadeClient

_LOGGER = logging.getLogger(__name__)


class LemonadeTtsHandler(AsyncEventHandler):
    """Handle one TTS client connection.

    Event flow:
        Describe   →  Info (with TtsProgram)
        Synthesize →  AudioStart + AudioChunk(s) + AudioStop
    """

    _READY_TIMEOUT = 600.0

    def __init__(
        self,
        wyoming_info: Info,
        client: LemonadeClient,
        tts_model: str,
        tts_voice: str,
        ready_event: asyncio.Event,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._info_event = wyoming_info.event()
        self._client = client
        self._model = tts_model
        self._voice = tts_voice
        self._ready_event = ready_event

    async def handle_event(self, event: Event) -> bool:  # noqa: D401
        if Describe.is_type(event.type):
            await self.write_event(self._info_event)
            _LOGGER.debug("Responded to Describe (TTS)")
            return True

        if Synthesize.is_type(event.type):
            synthesize = Synthesize.from_event(event)
            text = synthesize.text
            voice = self._voice
            if synthesize.voice and synthesize.voice.name:
                voice = synthesize.voice.name

            _LOGGER.info("Synthesize: voice=%s text=%r", voice, text[:80])

            if not self._ready_event.is_set():
                _LOGGER.info("Waiting for Lemonade setup to complete before synthesizing …")
                try:
                    await asyncio.wait_for(
                        self._ready_event.wait(), timeout=self._READY_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    _LOGGER.error("Timed out waiting for Lemonade — dropping TTS request")
                    await self.write_event(
                        AudioStart(
                            rate=KOKORO_SAMPLE_RATE,
                            width=KOKORO_SAMPLE_WIDTH,
                            channels=KOKORO_CHANNELS,
                        ).event()
                    )
                    await self.write_event(AudioStop().event())
                    return False

            try:
                await self._do_synthesize(text, voice)
            except Exception:
                _LOGGER.exception("TTS synthesis failed")
                # Send an empty audio sequence so the client doesn't hang
                await self.write_event(
                    AudioStart(
                        rate=KOKORO_SAMPLE_RATE,
                        width=KOKORO_SAMPLE_WIDTH,
                        channels=KOKORO_CHANNELS,
                    ).event()
                )
                await self.write_event(AudioStop().event())

            # Disconnect after synthesizing
            return False

        return True

    # ── internals ────────────────────────────────────────────────────────

    async def _do_synthesize(self, text: str, voice: str) -> None:
        """Stream PCM from Lemonade as Wyoming AudioChunk events."""
        # Signal audio start
        await self.write_event(
            AudioStart(
                rate=KOKORO_SAMPLE_RATE,
                width=KOKORO_SAMPLE_WIDTH,
                channels=KOKORO_CHANNELS,
            ).event()
        )

        bytes_sent = 0
        try:
            async for pcm_chunk in self._client.synthesize_speech_streaming(
                text=text,
                model=self._model,
                voice=voice,
            ):
                await self.write_event(
                    AudioChunk(
                        audio=pcm_chunk,
                        rate=KOKORO_SAMPLE_RATE,
                        width=KOKORO_SAMPLE_WIDTH,
                        channels=KOKORO_CHANNELS,
                    ).event()
                )
                bytes_sent += len(pcm_chunk)
        except Exception:
            _LOGGER.exception("Error during TTS streaming")

        # If streaming failed or returned nothing, fall back to non-streaming
        if bytes_sent == 0:
            _LOGGER.warning("Streaming returned no data — falling back to single request")
            try:
                pcm = await self._client.synthesize_speech(
                    text=text,
                    model=self._model,
                    voice=voice,
                )
                if pcm:
                    await self.write_event(
                        AudioChunk(
                            audio=pcm,
                            rate=KOKORO_SAMPLE_RATE,
                            width=KOKORO_SAMPLE_WIDTH,
                            channels=KOKORO_CHANNELS,
                        ).event()
                    )
            except Exception:
                _LOGGER.exception("Non-streaming TTS fallback also failed")

        await self.write_event(AudioStop().event())
        _LOGGER.debug("TTS done — sent %d bytes of audio", bytes_sent)
