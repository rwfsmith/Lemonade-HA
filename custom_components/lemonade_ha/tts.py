"""Lemonade HA — Text-to-Speech entity."""

from __future__ import annotations

import logging

from homeassistant.components.tts import TextToSpeechEntity, TtsAudioType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import LemonadeClient
from .const import (
    CONF_TTS_MODEL,
    CONF_TTS_VOICE,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    DOMAIN,
    KOKORO_CHANNELS,
    KOKORO_SAMPLE_RATE,
    KOKORO_SAMPLE_WIDTH,
)

_LOGGER = logging.getLogger(__name__)

SUPPORTED_VOICES = [
    "af_heart", "af_sky", "af_bella", "af_nicole", "af_sarah",
    "am_adam", "am_michael", "am_echo",
    "bf_emma", "bm_george",
    "alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "shimmer",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: LemonadeClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LemonadeTtsEntity(entry, client)])


class LemonadeTtsEntity(TextToSpeechEntity):
    """Kokoro TTS via Lemonade."""

    _attr_name = "Lemonade Kokoro"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, client: LemonadeClient) -> None:
        self._entry = entry
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_tts"

    @property
    def default_language(self) -> str:
        return "en"

    @property
    def supported_languages(self) -> list[str]:
        return ["en"]

    @property
    def default_options(self) -> dict:
        return {"voice": self._entry.data.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE)}

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict | None = None
    ) -> TtsAudioType:
        data = self._entry.options or self._entry.data
        model = data.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        voice = (options or {}).get("voice") or data.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE)

        try:
            pcm = await self._client.synthesize_speech(
                text=message, model=model, voice=voice
            )
        except Exception:
            _LOGGER.exception("Lemonade TTS synthesis failed")
            return None, None

        # Wrap raw PCM in a WAV container so HA knows how to play it
        wav = self._client.pcm_to_wav(
            pcm,
            sample_rate=KOKORO_SAMPLE_RATE,
            sample_width=KOKORO_SAMPLE_WIDTH,
            channels=KOKORO_CHANNELS,
        )
        return "wav", wav
