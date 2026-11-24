"""Conversation regressions without a Home Assistant install."""

from copy import deepcopy
from dataclasses import dataclass
import importlib.util
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from test_client import _COMPONENT, _PACKAGE


class IntentResponse:
    def __init__(self, language):
        self.language = language

    def async_set_speech(self, speech):
        self.speech = speech


@dataclass
class ConversationResult:
    response: IntentResponse
    conversation_id: str | None = None
    continue_conversation: bool = False


def load_conversation():
    modules = {
        f"homeassistant{suffix}": ModuleType(f"homeassistant{suffix}")
        for suffix in (
            "", ".components", ".components.conversation", ".config_entries",
            ".core", ".helpers", ".helpers.entity_platform",
        )
    }
    conversation = modules["homeassistant.components.conversation"]
    conversation.ConversationEntity = object
    conversation.ConversationInput = SimpleNamespace
    conversation.ConversationResult = ConversationResult
    modules["homeassistant.config_entries"].ConfigEntry = object
    modules["homeassistant.core"].HomeAssistant = object
    modules["homeassistant.helpers"].intent = SimpleNamespace(IntentResponse=IntentResponse)
    modules["homeassistant.helpers"].llm = SimpleNamespace()
    modules["homeassistant.helpers.entity_platform"].AddEntitiesCallback = object
    spec = importlib.util.spec_from_file_location(
        f"{_PACKAGE}.conversation", _COMPONENT / "conversation.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


conversation = load_conversation()


class SpeechTextTests(unittest.TestCase):
    def test_removes_emphasis_and_joke_emoji(self):
        self.assertEqual(
            conversation._speech_text(
                "**Why?** Because it's *funny*! \U0001f602 "
                "_Really_ __funny__ and ~~very~~ `clever`."
            ),
            "Why? Because it's funny! Really funny and very clever.",
        )

    def test_removes_lists_headings_links_and_code_fences(self):
        self.assertEqual(
            conversation._speech_text(
                "# Options\n- **Kitchen**\n* Hall\n1. Bedroom\n"
                "> Read [the guide](https://example.com).\n```text\nDone.\n```"
            ),
            "Options Kitchen Hall Bedroom Read the guide. Done.",
        )

    def test_removes_compound_emoji_but_preserves_numbers(self):
        self.assertEqual(
            conversation._speech_text(
                "Hi \U0001f44b\U0001f3fd! "
                "\U0001f468\u200d\U0001f469\u200d\U0001f467 "
                "\U0001f1ec\U0001f1e7 \u2764\ufe0f 1\ufe0f\u20e3 "
                "\u00a9\ufe0f 123 #4 *"
            ),
            "Hi ! 123 #4 *",
        )

    def test_preserves_non_english_text_and_meaningful_punctuation(self):
        text = "Caf\u00e9: 21\u00b0C, \u00a35. \u4f60\u597d! 2 * 3 = 6; room_name, don't, #4."
        self.assertEqual(conversation._speech_text(text), text)


class ConversationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.messages = []

        async def reply(*, messages, **kwargs):
            self.messages.append(deepcopy(messages))
            return "It's sunny today.", []

        self.client = SimpleNamespace(chat_completion=AsyncMock(side_effect=reply))
        self.settings = {}
        self.agent = conversation.LemonadeLlmEntity(
            SimpleNamespace(entry_id="entry"),
            SimpleNamespace(title="Lemonade", subentry_id="agent", data=self.settings),
            self.client,
        )
        self.agent.hass = object()
        tools = patch.object(
            conversation, "_get_llm_tools", return_value=([], "system prompt", None)
        )
        tools.start()
        self.addCleanup(tools.stop)

    async def turn(self, text, conversation_id=None, user_id="alice"):
        return await self.agent.async_process(SimpleNamespace(
            text=text, conversation_id=conversation_id, language="en-US",
            context=SimpleNamespace(user_id=user_id),
        ))

    async def test_default_is_off_but_an_explicit_id_still_keeps_context(self):
        first = await self.turn("What's the weather?", "existing-session")
        follow_up = await self.turn("And tomorrow?", first.conversation_id)

        self.assertEqual(follow_up.conversation_id, "existing-session")
        self.assertFalse(first.continue_conversation)
        self.assertFalse(follow_up.continue_conversation)
        self.assertEqual(self.messages[-1][1]["content"], "What's the weather?")

    async def test_opt_in_requests_follow_up_even_after_a_statement(self):
        self.settings[conversation.CONF_LLM_CONTINUE_CONVERSATION] = True
        first = await self.turn("What's the weather?")
        follow_up = await self.turn("And tomorrow?", first.conversation_id)

        self.assertTrue(first.continue_conversation)
        self.assertTrue(follow_up.continue_conversation)
        self.assertEqual(follow_up.conversation_id, first.conversation_id)
        self.assertEqual(
            [message["content"] for message in self.messages[-1][1:]],
            ["What's the weather?", "It's sunny today.", "And tomorrow?"],
        )

    async def test_fresh_chats_and_different_users_do_not_share_history(self):
        first = await self.turn("A private request")
        fresh = await self.turn("New request")
        await self.turn("Another user", first.conversation_id, user_id="bob")

        self.assertTrue(first.conversation_id)
        self.assertNotEqual(first.conversation_id, fresh.conversation_id)
        self.assertEqual([len(messages) for messages in self.messages], [2, 2, 2])

    async def test_stop_ends_the_session_without_calling_the_model(self):
        self.settings[conversation.CONF_LLM_CONTINUE_CONVERSATION] = True
        first = await self.turn("What's the weather?")
        stopped = await self.turn(" Stop listening! ", first.conversation_id)

        self.assertFalse(stopped.continue_conversation)
        self.assertEqual(self.client.chat_completion.await_count, 1)
        await self.turn("New topic", first.conversation_id)
        self.assertEqual(len(self.messages[-1]), 2)

    async def test_failed_reply_does_not_continue_or_leave_an_unanswered_turn(self):
        self.settings[conversation.CONF_LLM_CONTINUE_CONVERSATION] = True
        first = await self.turn("What's the weather?")
        reply = self.client.chat_completion.side_effect
        self.client.chat_completion.side_effect = RuntimeError("Connection lost")
        with self.assertLogs(conversation.__name__, level="ERROR"):
            failure = await self.turn("Failed request", first.conversation_id)
        self.assertFalse(failure.continue_conversation)

        self.client.chat_completion.side_effect = reply
        await self.turn("Retry", first.conversation_id)
        self.assertNotIn("Failed request", [msg["content"] for msg in self.messages[-1]])

    async def test_empty_reply_does_not_continue(self):
        self.settings[conversation.CONF_LLM_CONTINUE_CONVERSATION] = True
        self.client.chat_completion.side_effect = None
        self.client.chat_completion.return_value = (" ", [])
        with self.assertLogs(conversation.__name__, level="WARNING"):
            result = await self.turn("What's the weather?")

        self.assertFalse(result.continue_conversation)
        self.assertIn("couldn't process", result.response.speech)

    async def test_voice_instructions_apply_to_saved_custom_prompts(self):
        self.settings[conversation.CONF_LLM_SYSTEM_PROMPT] = "Tell jokes."
        with patch.object(
            conversation, "_get_llm_tools",
            return_value=([], "Tell jokes.\n\nAssist tool instructions.", None),
        ) as get_tools:
            await self.turn("Tell me a joke")
        self.assertEqual(get_tools.call_args.args[2], "Tell jokes.")
        system = self.messages[-1][0]["content"]
        self.assertTrue(system.startswith("Tell jokes.\n\nAssist tool instructions."))
        self.assertIn("plain spoken text only", system)
        self.assertIn("emoji", system)

    async def test_speech_and_follow_up_history_are_plain_text(self):
        self.client.chat_completion.side_effect = None
        self.client.chat_completion.return_value = ("**A joke!** \U0001f602", [])
        first = await self.turn("Tell a joke")
        self.assertEqual(first.response.speech, "A joke!")

        self.client.chat_completion.side_effect = (
            lambda **kwargs: self.messages.append(deepcopy(kwargs["messages"]))
            or ("Another joke.", [])
        )
        await self.turn("Another", first.conversation_id)
        self.assertEqual(self.messages[-1][-2]["content"], "A joke!")

    async def test_emoji_only_reply_does_not_continue_or_enter_history(self):
        self.settings[conversation.CONF_LLM_CONTINUE_CONVERSATION] = True
        self.client.chat_completion.side_effect = None
        self.client.chat_completion.return_value = ("**\U0001f602**", [])
        with self.assertLogs(conversation.__name__, level="WARNING"):
            result = await self.turn("Tell a joke")
        self.assertFalse(result.continue_conversation)
        self.assertIn("couldn't process", result.response.speech)
        self.assertFalse(self.agent._histories)

    async def test_tool_unavailable_reply_is_also_plain_text(self):
        self.client.chat_completion.side_effect = None
        self.client.chat_completion.return_value = (
            "**No access.** \U0001f614",
            [{"id": "call", "function": {"name": "test", "arguments": "{}"}}],
        )
        with self.assertLogs(conversation.__name__, level="WARNING"):
            result = await self.turn("Turn on the light")
        self.assertEqual(result.response.speech, "No access.")
