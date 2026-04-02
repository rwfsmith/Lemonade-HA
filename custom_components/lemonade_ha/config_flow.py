"""Config flow for Lemonade HA."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigSubentryFlow
from homeassistant.core import callback

from .const import (
    CONF_HOST,
    CONF_LLM_MAX_TOKENS,
    CONF_LLM_MODEL,
    CONF_LLM_SYSTEM_PROMPT,
    CONF_PORT,
    CONF_STT_LANGUAGE,
    CONF_STT_MODEL,
    CONF_TTS_MODEL,
    CONF_TTS_VOICE,
    DEFAULT_HOST,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_MODEL,
    DEFAULT_PORT,
    DEFAULT_STT_LANGUAGE,
    DEFAULT_STT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    DOMAIN,
)
from .tts import SUPPORTED_VOICES

_LOGGER = logging.getLogger(__name__)


# ── Schema helpers ─────────────────────────────────────────────────────────────

def _model_selector(models: list[str] | None, default: str) -> vol.Schema:
    """Return vol.In dropdown if models are known, else free-text str."""
    if models:
        options = models if default in models else [default, *models]
        return vol.In(options)
    return str


def _stt_schema(defaults: dict, models: list[str] | None = None) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_STT_MODEL, default=defaults.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)):
            _model_selector(models, defaults.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)),
        vol.Required(CONF_STT_LANGUAGE, default=defaults.get(CONF_STT_LANGUAGE, DEFAULT_STT_LANGUAGE)): str,
    })


def _llm_schema(defaults: dict, models: list[str] | None = None) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_LLM_MODEL, default=defaults.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL)):
            _model_selector(models, defaults.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL)),
        vol.Optional(CONF_LLM_SYSTEM_PROMPT, default=defaults.get(CONF_LLM_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)): str,
        vol.Optional(CONF_LLM_MAX_TOKENS, default=defaults.get(CONF_LLM_MAX_TOKENS, DEFAULT_LLM_MAX_TOKENS)): vol.Coerce(int),
    })


def _tts_schema(defaults: dict) -> vol.Schema:
    # Voice dropdown: {voice_id: "Friendly Name"} dict renders as a labelled selector
    voice_options = {voice_id: name for voice_id, name in SUPPORTED_VOICES}
    default_voice = defaults.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE)
    if default_voice not in voice_options:
        voice_options[default_voice] = default_voice
    return vol.Schema({
        vol.Required(CONF_TTS_MODEL, default=defaults.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)): str,
        vol.Required(CONF_TTS_VOICE, default=default_voice): vol.In(voice_options),
    })


async def _fetch_models(hass, entry_id: str, kind: str = "llm") -> list[str]:
    """Fetch model IDs from Lemonade, filtered by kind ('stt' or 'llm')."""
    from .client import LemonadeClient
    entry = hass.config_entries.async_get_known_entry(entry_id)
    client = LemonadeClient(entry.data[CONF_HOST], entry.data[CONF_PORT])
    try:
        all_models = await client.get_models()
    except Exception:
        return []
    finally:
        await client.close()
    if kind == "stt":
        return [m for m in all_models if "whisper" in m.lower()]
    # llm: exclude whisper and kokoro/tts models
    return [m for m in all_models if "whisper" not in m.lower() and "kokoro" not in m.lower()]


# ── Subentry flows ─────────────────────────────────────────────────────────────

class SttSubentryFlow(ConfigSubentryFlow):
    """Add or reconfigure a Whisper STT service."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> dict:
        if user_input is not None:
            return self.async_create_entry(title="Lemonade STT", data=user_input)
        models = await _fetch_models(self.hass, self._entry_id, kind="stt")
        return self.async_show_form(step_id="user", data_schema=_stt_schema({}, models))

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> dict:
        current = self._get_reconfigure_subentry()
        if user_input is not None:
            return self.async_update_and_abort(
                self._get_entry(), current, data=user_input, title="Lemonade STT"
            )
        models = await _fetch_models(self.hass, self._entry_id, kind="stt")
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_stt_schema(current.data, models),
        )


class LlmSubentryFlow(ConfigSubentryFlow):
    """Add or reconfigure an LLM conversation service."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> dict:
        if user_input is not None:
            return self.async_create_entry(title="Lemonade", data=user_input)
        models = await _fetch_models(self.hass, self._entry_id, kind="llm")
        return self.async_show_form(step_id="user", data_schema=_llm_schema({}, models))

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> dict:
        current = self._get_reconfigure_subentry()
        if user_input is not None:
            return self.async_update_and_abort(
                self._get_entry(), current, data=user_input, title="Lemonade"
            )
        models = await _fetch_models(self.hass, self._entry_id, kind="llm")
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_llm_schema(current.data, models),
        )


class TtsSubentryFlow(ConfigSubentryFlow):
    """Add or reconfigure a Kokoro TTS service."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> dict:
        if user_input is not None:
            return self.async_create_entry(
                title=f"Kokoro ({user_input[CONF_TTS_VOICE]})",
                data=user_input,
            )
        return self.async_show_form(step_id="user", data_schema=_tts_schema({}))

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> dict:
        current = self._get_reconfigure_subentry()
        if user_input is not None:
            return self.async_update_and_abort(
                self._get_entry(), current,
                data=user_input,
                title=f"Kokoro ({user_input[CONF_TTS_VOICE]})",
            )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_tts_schema(current.data),
        )


# ── Main config flow ───────────────────────────────────────────────────────────

class LemonadeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lemonade HA."""

    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return supported subentry types."""
        return {
            "stt": SttSubentryFlow,
            "llm": LlmSubentryFlow,
            "tts": TtsSubentryFlow,
        }

    def __init__(self) -> None:
        self._host: str = DEFAULT_HOST
        self._port: int = DEFAULT_PORT

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> dict:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input[CONF_PORT]
            from .client import LemonadeClient
            client = LemonadeClient(self._host, self._port)
            try:
                if not await client.health_check():
                    errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "cannot_connect"
            finally:
                await client.close()

            if not errors:
                await self.async_set_unique_id(f"{self._host}:{self._port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Lemonade ({self._host}:{self._port})",
                    data={CONF_HOST: self._host, CONF_PORT: self._port},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
            }),
            errors=errors,
        )
