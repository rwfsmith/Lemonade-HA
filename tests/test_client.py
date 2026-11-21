"""Client request regressions runnable without a Home Assistant installation."""

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock


_COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "lemonade_ha"
_PACKAGE = "_lemonade_client_tests"
package = ModuleType(_PACKAGE)
package.__path__ = [str(_COMPONENT)]
sys.modules[_PACKAGE] = package
spec = importlib.util.spec_from_file_location(f"{_PACKAGE}.client", _COMPONENT / "client.py")
client_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = client_module
spec.loader.exec_module(client_module)
LemonadeClient = client_module.LemonadeClient


class StreamingResponse:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def raise_for_status(self):
        pass

    @property
    def content(self):
        async def lines():
            event = {"choices": [{"delta": {"content": "<think>hidden</think>Hello"}}]}
            yield f"data: {json.dumps(event)}\n".encode()
            yield b"data: [DONE]\n"

        return lines()


class ChatCompletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = LemonadeClient("localhost", 8000)
        self.session = Mock()
        self.session.post.return_value = StreamingResponse()
        self.client._get_session = Mock(return_value=self.session)

    async def test_each_effort_is_sent_without_disabling_qwen_thinking(self):
        messages = [{"role": "system", "content": "Be concise."}]
        tools = [{"type": "function", "function": {"name": "test"}}]
        for effort in ("minimal", "low", "medium", "high", "xhigh", "max"):
            with self.subTest(effort=effort):
                result = await self.client.chat_completion(
                    messages, "Qwen3-4B-GGUF", max_tokens=1024,
                    tools=tools, reasoning_effort=effort,
                )
                body = self.session.post.call_args.kwargs["json"]
                self.assertEqual(body["reasoning_effort"], effort)
                self.assertEqual(body["messages"], messages)
                self.assertNotIn("enable_thinking", body)
                self.assertNotIn("chat_template_kwargs", body)
                self.assertEqual(body["tools"], tools)
                self.assertEqual(body["max_tokens"], 1024)
                self.assertEqual(result, ("Hello", []))
        self.assertEqual(messages, [{"role": "system", "content": "Be concise."}])

    async def test_unconfigured_qwen_retains_legacy_no_thinking(self):
        for messages in (
            [{"role": "system", "content": "Be concise."}],
            [{"role": "user", "content": "Hello"}],
        ):
            with self.subTest(messages=messages):
                original = [dict(message) for message in messages]
                await self.client.chat_completion(messages, "Qwen3-4B-GGUF")
                body = self.session.post.call_args.kwargs["json"]
                self.assertNotIn("reasoning_effort", body)
                self.assertFalse(body["enable_thinking"])
                self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
                self.assertIn("/no_think", body["messages"][0]["content"])
                self.assertEqual(messages, original)

    async def test_non_qwen_and_explicit_prompt_switch_are_preserved(self):
        messages = [{"role": "system", "content": "Be concise. /no_think"}]
        await self.client.chat_completion(messages, "other-model")
        body = self.session.post.call_args.kwargs["json"]
        self.assertNotIn("reasoning_effort", body)
        self.assertEqual(body["messages"], messages)
        await self.client.chat_completion(
            messages, "Qwen3-4B-GGUF", reasoning_effort="high"
        )
        self.assertEqual(self.session.post.call_args.kwargs["json"]["messages"], messages)

    async def test_invalid_effort_fails_before_request(self):
        with self.assertRaisesRegex(ValueError, "Unsupported reasoning effort"):
            await self.client.chat_completion([], "Qwen3-4B-GGUF", reasoning_effort="invalid")
        self.session.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
