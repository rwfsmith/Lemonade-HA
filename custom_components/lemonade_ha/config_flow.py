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

_LOGGER = logging.getLogger(__name__)


# ── Schema helpers ─────────────────────────────────────────────────────────────

def _stt_schema(defaults: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_STT_MODEL, default=defaults.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)): str,
        vol.Required(CONF_STT_LANGUAGE, default=defaults.get(CONF_STT_LANGUAGE, DEFAULT_STT_LANGUAGE)): str,
    })


def _llm_schema(defaults: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_LLM_MODEL, default=defaults.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL)): str,
        vol.Optional(CONF_LLM_SYSTEM_PROMPT, default=defaults.get(CONF_LLM_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)): str,
        vol.Optional(CONF_LLM_MAX_TOKENS, default=defaults.get(CONF_LLM_MAX_TOKENS, DEFAULT_LLM_MAX_TOKENS)): vol.Coerce(int),
    })


def _tts_schema(defaults: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_TTS_MODEL, default=defaults.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)): str,
        vol.Required(CONF_TTS_VOICE, default=defaults.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE)): str,
    })


# ── Subentry flows ─────────────────────────────────────────────────────────────

class SttSubentryFlow(ConfigSubentryFlow):
    """Add or reconfigure a Whisper STT service."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> dict:
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_STT_MODEL],
                data=user_input,
            )
        return self.async_show_form(step_id="user", data_schema=_stt_schema({}))

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> dict:
        current = self._get_reconfigure_subentry()
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_STT_MODEL],
                data=user_input,
            )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_stt_schema(current.data),
        )


class LlmSubentryFlow(ConfigSubentryFlow):
    """Add or reconfigure an LLM conversation service."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> dict:
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_LLM_MODEL],
                data=user_input,
            )
        return self.async_show_form(step_id="user", data_schema=_llm_schema({}))

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> dict:
        current = self._get_reconfigure_subentry()
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_LLM_MODEL],
                data=user_input,
            )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_llm_schema(current.data),
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
            return self.async_create_entry(
                title=f"Kokoro ({user_input[CONF_TTS_VOICE]})",
                data=user_input,
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
