"""Lemonade HA — Speech-to-Text entity."""

from __future__ import annotations

import logging
from typing import AsyncIterable

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import LemonadeClient
from .const import (
    CONF_STT_LANGUAGE,
    CONF_STT_MODEL,
    DEFAULT_STT_LANGUAGE,
    DEFAULT_STT_MODEL,
    DOMAIN,
    WHISPER_CHANNELS,
    WHISPER_SAMPLE_RATE,
    WHISPER_SAMPLE_WIDTH,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: LemonadeClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LemonadeSttEntity(entry, client)])


class LemonadeSttEntity(SpeechToTextEntity):
    """Whisper STT via Lemonade."""

    _attr_name = "Lemonade Whisper"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, client: LemonadeClient) -> None:
        self._entry = entry
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_stt"

    @property
    def supported_languages(self) -> list[str]:
        return [
            "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo",
            "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es",
            "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw",
            "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja",
            "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo",
            "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt",
            "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt",
            "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq",
            "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl",
            "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue", "zh",
        ]

    @property
    def supported_formats(self) -> list[AudioFormats]:
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        return [AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        return [AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> SpeechResult:
        # Collect raw PCM bytes from the stream
        pcm = b""
        async for chunk in stream:
            pcm += chunk

        if not pcm:
            _LOGGER.warning("STT received empty audio stream")
            return SpeechResult("", SpeechResultState.ERROR)

        # Wrap PCM in a WAV container for Lemonade
        wav_bytes = self._client.pcm_to_wav(
            pcm,
            sample_rate=metadata.sample_rate,
            sample_width=metadata.bit_rate // 8,
            channels=metadata.channel,
        )

        data = self._entry.options or self._entry.data
        model = data.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)
        language = metadata.language or data.get(CONF_STT_LANGUAGE, DEFAULT_STT_LANGUAGE)

        try:
            text = await self._client.transcribe(wav_bytes, model=model, language=language)
        except Exception:
            _LOGGER.exception("Lemonade STT transcription failed")
            return SpeechResult("", SpeechResultState.ERROR)

        _LOGGER.info("STT transcript: %r", text)
        return SpeechResult(text, SpeechResultState.SUCCESS)
