"""Lemonade HA — Conversation agent entity."""

from __future__ import annotations

from collections import OrderedDict
import json
import logging
from typing import Any, Literal
from uuid import uuid4

from homeassistant.components import conversation as ha_conversation
from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationInput,
    ConversationResult,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent, llm
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import LemonadeClient
from .const import (
    CONF_LLM_CONTINUE_CONVERSATION,
    CONF_LLM_MAX_TOKENS,
    CONF_LLM_MODEL,
    CONF_LLM_REASONING_EFFORT,
    CONF_LLM_SYSTEM_PROMPT,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 10
_MAX_HISTORIES = 128
_MAX_HISTORY_TURNS = 10
_STOP_PHRASES = {"end conversation", "stop listening"}


def _tool_to_openai(tool: llm.Tool) -> dict:
    """Convert an HA LLM Tool to an OpenAI-compatible function definition."""
    try:
        from voluptuous_openapi import convert
        params = convert(tool.parameters)
    except Exception:
        params = {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": params,
        },
    }


async def _get_llm_tools(
    hass: HomeAssistant, user_input: ConversationInput, system_prompt: str
) -> tuple[list[dict], str, Any]:
    """Try to fetch HA Assist tools. Returns (tools, full_system_prompt).

    Falls back to ([], system_prompt) on any error so conversation still works.
    """
    try:
        # LLMContext signature varies across HA versions — build kwargs defensively.
        import inspect
        llm_ctx_params = set(inspect.signature(llm.LLMContext.__init__).parameters)
        ctx_kwargs: dict[str, Any] = {"platform": DOMAIN, "context": user_input.context}
        if "language" in llm_ctx_params:
            ctx_kwargs["language"] = user_input.language
        if "user_prompt" in llm_ctx_params:
            ctx_kwargs["user_prompt"] = user_input.text
        if "assistant" in llm_ctx_params:
            ctx_kwargs["assistant"] = ha_conversation.HOME_ASSISTANT_AGENT
        if "device_id" in llm_ctx_params:
            ctx_kwargs["device_id"] = user_input.device_id
        llm_context = llm.LLMContext(**ctx_kwargs)
        llm_api = await llm.async_get_api(hass, "assist", llm_context)
        tools = [_tool_to_openai(t) for t in llm_api.tools]
        full_system = f"{system_prompt}\n\n{llm_api.api_prompt}"
        _LOGGER.debug("Loaded %d HA tools", len(tools))
        return tools, full_system, llm_api
    except Exception:
        _LOGGER.debug("HA LLM tools unavailable, running without tool calling", exc_info=True)
        return [], system_prompt, None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: LemonadeClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        LemonadeLlmEntity(entry, subentry, client)
        for subentry in entry.subentries.values()
        if subentry.subentry_type == "llm"
    ])


class LemonadeLlmEntity(ConversationEntity):
    """LLM conversation agent via Lemonade — one entity per LLM subentry."""

    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry, subentry: Any, client: LemonadeClient) -> None:
        self._entry = entry
        self._subentry = subentry
        self._client = client
        self._attr_name = subentry.title
        self._attr_unique_id = f"{entry.entry_id}_llm_{subentry.subentry_id}"
        self._histories: OrderedDict[tuple[str | None, str], list[list[dict]]] = (
            OrderedDict()
        )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return "*"

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        try:
            return await self._async_process(user_input)
        except Exception:
            _LOGGER.exception("Unexpected error in Lemonade conversation agent")
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech("Sorry, an unexpected error occurred.")
            return ConversationResult(response=intent_response, conversation_id=None)

    async def _async_process(self, user_input: ConversationInput) -> ConversationResult:
        data = self._subentry.data
        model = data.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL)
        system_prompt = data.get(CONF_LLM_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)
        max_tokens = int(data.get(CONF_LLM_MAX_TOKENS, DEFAULT_LLM_MAX_TOKENS))
        reasoning_effort = data.get(CONF_LLM_REASONING_EFFORT)
        continue_enabled = data.get(CONF_LLM_CONTINUE_CONVERSATION, False)

        conv_id = user_input.conversation_id or uuid4().hex
        session_key = (user_input.context.user_id, conv_id)
        if (
            continue_enabled
            and user_input.language.lower().split("-")[0] == "en"
            and user_input.text.strip().rstrip(".!?").casefold() in _STOP_PHRASES
        ):
            self._histories.pop(session_key, None)
            response = intent.IntentResponse(language=user_input.language)
            response.async_set_speech("Okay, I'll stop listening.")
            return ConversationResult(response=response, conversation_id=conv_id)

        # ── Fetch HA Assist tools ───────────────────────────────────────────
        tools, full_system, llm_api = await _get_llm_tools(
            self.hass, user_input, system_prompt
        )

        # ── Conversation history ────────────────────────────────────────────
        past_turns = self._histories.get(session_key, [])
        history = [{"role": "system", "content": full_system}]
        for turn in past_turns:
            history.extend(turn)
        turn_start = len(history)
        history.append({"role": "user", "content": user_input.text})

        # ── Tool call loop ──────────────────────────────────────────────────
        response_text = "Sorry, I couldn't process that request."
        completed = False
        for iteration in range(_MAX_TOOL_ITERATIONS):
            try:
                content, tool_calls = await self._client.chat_completion(
                    messages=history,
                    model=model,
                    max_tokens=max_tokens,
                    tools=tools or None,
                    reasoning_effort=reasoning_effort,
                )
            except Exception:
                _LOGGER.exception("Lemonade LLM chat completion failed")
                break

            if not tool_calls:
                if not content.strip():
                    _LOGGER.warning("Lemonade returned an empty conversation response")
                    break
                response_text = content
                history.append({"role": "assistant", "content": response_text})
                completed = True
                break

            # Model wants to call tools
            _LOGGER.debug(
                "Tool call(s) requested (iteration %d): %s",
                iteration,
                [tc["function"]["name"] for tc in tool_calls],
            )
            history.append({
                "role": "assistant",
                "content": content or None,
                "tool_calls": tool_calls,
            })

            if llm_api is None:
                _LOGGER.warning("Tool calls requested but HA LLM API is unavailable")
                response_text = content or "I need smart-home access to answer that."
                break

            # Execute each tool and append results
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    tool_args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    tool_args = {}
                try:
                    result = await llm_api.async_call_tool(
                        llm.ToolInput(tool_name=tool_name, tool_args=tool_args)
                    )
                    result_str = json.dumps(result)
                    _LOGGER.debug("Tool %s(%s) → %s", tool_name, tool_args, result_str)
                except Exception as exc:
                    result_str = json.dumps({"error": str(exc)})
                    _LOGGER.warning("Tool %s failed: %s", tool_name, exc)
                history.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_str,
                })
        else:
            _LOGGER.warning("Tool loop hit max iterations (%d)", _MAX_TOOL_ITERATIONS)

        if completed:
            # Keep complete turns so pruning cannot split a tool call from its results.
            self._histories[session_key] = [*past_turns, history[turn_start:]][
                -_MAX_HISTORY_TURNS:
            ]
            self._histories.move_to_end(session_key)
            if len(self._histories) > _MAX_HISTORIES:
                self._histories.popitem(last=False)

        _LOGGER.info("LLM: %r → %r", user_input.text, response_text)

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)
        result = ConversationResult(response=intent_response, conversation_id=conv_id)
        # Home Assistant versions before 2025.4 do not expose this flag.
        if continue_enabled and completed and hasattr(result, "continue_conversation"):
            result.continue_conversation = True
        return result
