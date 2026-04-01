"""Config flow for Lemonade HA."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .client import LemonadeClient
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

_CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
    }
)

_MODEL_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_STT_MODEL, default=DEFAULT_STT_MODEL): str,
        vol.Optional(CONF_STT_LANGUAGE, default=DEFAULT_STT_LANGUAGE): str,
        vol.Optional(CONF_LLM_MODEL, default=DEFAULT_LLM_MODEL): str,
        vol.Optional(CONF_LLM_SYSTEM_PROMPT, default=DEFAULT_SYSTEM_PROMPT): str,
        vol.Optional(CONF_LLM_MAX_TOKENS, default=DEFAULT_LLM_MAX_TOKENS): vol.Coerce(int),
        vol.Optional(CONF_TTS_MODEL, default=DEFAULT_TTS_MODEL): str,
        vol.Optional(CONF_TTS_VOICE, default=DEFAULT_TTS_VOICE): str,
    }
)


class LemonadeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lemonade HA."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str = DEFAULT_HOST
        self._port: int = DEFAULT_PORT

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input[CONF_PORT]
            client = LemonadeClient(self._host, self._port)
            try:
                if not await client.health_check():
                    errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "cannot_connect"
            finally:
                await client.close()

            if not errors:
                return await self.async_step_models()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._host): str,
                    vol.Required(CONF_PORT, default=self._port): vol.Coerce(int),
                }
            ),
            errors=errors,
        )

    async def async_step_models(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            data = {
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                **user_input,
            }
            await self.async_set_unique_id(f"{self._host}:{self._port}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Lemonade HA", data=data)

        return self.async_show_form(
            step_id="models",
            data_schema=_MODEL_SCHEMA,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LemonadeOptionsFlow(config_entry)


class LemonadeOptionsFlow(OptionsFlow):
    """Allow reconfiguring models without re-entering host/port."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = self._entry.data
        schema = vol.Schema(
            {
                vol.Optional(CONF_STT_MODEL, default=data.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)): str,
                vol.Optional(CONF_STT_LANGUAGE, default=data.get(CONF_STT_LANGUAGE, DEFAULT_STT_LANGUAGE)): str,
                vol.Optional(CONF_LLM_MODEL, default=data.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL)): str,
                vol.Optional(CONF_LLM_SYSTEM_PROMPT, default=data.get(CONF_LLM_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)): str,
                vol.Optional(CONF_LLM_MAX_TOKENS, default=data.get(CONF_LLM_MAX_TOKENS, DEFAULT_LLM_MAX_TOKENS)): vol.Coerce(int),
                vol.Optional(CONF_TTS_MODEL, default=data.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)): str,
                vol.Optional(CONF_TTS_VOICE, default=data.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE)): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
