"""Lemonade HA — Text-to-Speech entity."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from homeassistant.components.tts import TextToSpeechEntity, TtsAudioType, Voice
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

# Split on sentence-ending punctuation followed by whitespace or end-of-string.
# Keeps the punctuation attached to the preceding chunk.
# Avoids splitting on common abbreviations (Mr. Dr. etc.) by requiring the
# character before the punctuation to not be a single capital letter.
_SENTENCE_RE = re.compile(r'(?<=[^A-Z][\.\!\?])\s+')


def _split_sentences(text: str, min_len: int = 40) -> list[str]:
    """Split text into sentence chunks for parallel TTS synthesis.

    Chunks shorter than min_len are merged with the next one so Kokoro
    doesn't produce choppy one-word clips.
    """
    raw = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
    if not raw:
        return [text]
    merged: list[str] = []
    buf = ""
    for chunk in raw:
        buf = (buf + " " + chunk).strip() if buf else chunk
        if len(buf) >= min_len:
            merged.append(buf)
            buf = ""
    if buf:
        if merged:
            merged[-1] += " " + buf  # attach trailing fragment to previous
        else:
            merged.append(buf)
    return merged


# (voice_id, friendly name)
SUPPORTED_VOICES: list[tuple[str, str]] = [
    # American Female
    ("af_heart",   "Heart (American Female)"),
    ("af_sky",     "Sky (American Female)"),
    ("af_bella",   "Bella (American Female)"),
    ("af_nicole",  "Nicole (American Female)"),
    ("af_sarah",   "Sarah (American Female)"),
    ("af_alloy",   "Alloy (American Female)"),
    # American Male
    ("am_adam",    "Adam (American Male)"),
    ("am_michael", "Michael (American Male)"),
    ("am_echo",    "Echo (American Male)"),
    # British Female
    ("bf_emma",    "Emma (British Female)"),
    # British Male
    ("bm_george",  "George (British Male)"),
    # OpenAI-compatible aliases
    ("alloy",      "Alloy"),
    ("ash",        "Ash"),
    ("coral",      "Coral"),
    ("echo",       "Echo"),
    ("fable",      "Fable"),
    ("onyx",       "Onyx"),
    ("nova",       "Nova"),
    ("shimmer",    "Shimmer"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: LemonadeClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        LemonadeTtsEntity(entry, subentry, client)
        for subentry in entry.subentries.values()
        if subentry.subentry_type == "tts"
    ])


class LemonadeTtsEntity(TextToSpeechEntity):
    """Kokoro TTS via Lemonade — one entity per TTS subentry."""

    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry, subentry: Any, client: LemonadeClient) -> None:
        self._entry = entry
        self._subentry = subentry
        self._client = client
        self._attr_name = subentry.title
        self._attr_unique_id = f"{entry.entry_id}_tts_{subentry.subentry_id}"

    @property
    def default_language(self) -> str:
        return "en"

    @property
    def supported_languages(self) -> list[str]:
        return ["en"]

    @property
    def supported_options(self) -> list[str]:
        return ["voice"]

    @property
    def default_options(self) -> dict:
        return {"voice": self._subentry.data.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE)}

    async def async_get_tts_voice_list(self) -> list[Voice]:
        return [Voice(voice_id=vid, name=name) for vid, name in SUPPORTED_VOICES]

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict | None = None
    ) -> TtsAudioType:
        data = self._subentry.data
        model = data.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        voice = (options or {}).get("voice") or data.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE)

        sentences = _split_sentences(message)
        _LOGGER.debug("TTS: synthesising %d chunk(s) in parallel", len(sentences))

        try:
            pcm_chunks: list[bytes] = list(await asyncio.gather(
                *[self._client.synthesize_speech(s, model=model, voice=voice)
                  for s in sentences]
            ))
        except Exception:
            _LOGGER.exception("Lemonade TTS synthesis failed")
            return None, None

        combined_pcm = b"".join(pcm_chunks)
        # Wrap raw PCM in a WAV container so HA knows how to play it
        wav = self._client.pcm_to_wav(
            combined_pcm,
            sample_rate=KOKORO_SAMPLE_RATE,
            sample_width=KOKORO_SAMPLE_WIDTH,
            channels=KOKORO_CHANNELS,
        )
        return "wav", wav
