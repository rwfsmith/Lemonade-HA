"""Lemonade HA — Conversation agent entity."""

from __future__ import annotations

import logging
from typing import Literal

from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationInput,
    ConversationResult,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import LemonadeClient
from .const import (
    CONF_LLM_MAX_TOKENS,
    CONF_LLM_MODEL,
    CONF_LLM_SYSTEM_PROMPT,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: LemonadeClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LemonadeLlmEntity(entry, client)])


class LemonadeLlmEntity(ConversationEntity):
    """LLM conversation agent via Lemonade."""

    _attr_name = "Lemonade LLM"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, client: LemonadeClient) -> None:
        self._entry = entry
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_conversation"
        # Per-conversation history: conversation_id -> list of messages
        self._histories: dict[str, list[dict[str, str]]] = {}

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return "*"

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        data = self._entry.options or self._entry.data
        model = data.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL)
        system_prompt = data.get(CONF_LLM_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)
        max_tokens = int(data.get(CONF_LLM_MAX_TOKENS, DEFAULT_LLM_MAX_TOKENS))

        # Retrieve or create conversation history
        conv_id = user_input.conversation_id or ""
        if conv_id not in self._histories:
            self._histories[conv_id] = [
                {"role": "system", "content": system_prompt}
            ]
        history = self._histories[conv_id]
        history.append({"role": "user", "content": user_input.text})

        try:
            response_text = await self._client.chat_completion(
                messages=history,
                model=model,
                max_tokens=max_tokens,
            )
        except Exception:
            _LOGGER.exception("Lemonade LLM chat completion failed")
            response_text = "Sorry, I couldn't process that request."

        history.append({"role": "assistant", "content": response_text})

        # Trim very long histories to avoid huge payloads (keep system + last 20)
        if len(history) > 22:
            self._histories[conv_id] = [history[0]] + history[-20:]

        _LOGGER.info("LLM: %r -> %r", user_input.text, response_text)

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)
        return ConversationResult(
            response=intent_response,
            conversation_id=conv_id or None,
        )
