"""Wyoming Conversation / Intent handler — bridges to Lemonade's LLM API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from wyoming.event import Event
from wyoming.handle import Handled, NotHandled
from wyoming.info import Describe, Info
from wyoming.asr import Transcript
from wyoming.server import AsyncEventHandler

from .lemonade_client import LemonadeClient

_LOGGER = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful smart-home voice assistant called Lemonade. "
    "Answer concisely in one or two sentences unless asked for more detail."
)


class LemonadeLlmHandler(AsyncEventHandler):
    """Handle one conversation / intent-handling client connection.

    Event flow:
        Describe   →  Info (with HandleProgram)
        Transcript →  Handled (LLM response text)
    """

    _READY_TIMEOUT = 600.0

    def __init__(
        self,
        wyoming_info: Info,
        client: LemonadeClient,
        llm_model: str,
        system_prompt: str,
        max_tokens: int,
        ready_event: asyncio.Event,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._info_event = wyoming_info.event()
        self._client = client
        self._model = llm_model
        self._system_prompt = system_prompt or _DEFAULT_SYSTEM_PROMPT
        self._max_tokens = max_tokens
        self._ready_event = ready_event

        # Simple per-connection message history (no cross-connection memory)
        self._messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
        ]

    async def handle_event(self, event: Event) -> bool:  # noqa: D401
        if Describe.is_type(event.type):
            await self.write_event(self._info_event)
            _LOGGER.debug("Responded to Describe (LLM)")
            return True

        if Transcript.is_type(event.type):
            if not self._ready_event.is_set():
                _LOGGER.info("Waiting for Lemonade setup to complete before running LLM …")
                try:
                    await asyncio.wait_for(
                        self._ready_event.wait(), timeout=self._READY_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    _LOGGER.error("Timed out waiting for Lemonade — dropping LLM request")
                    await self.write_event(
                        NotHandled(text="Lemonade is not yet ready.").event()
                    )
                    return False

            transcript = Transcript.from_event(event)
            user_text = transcript.text
            if not user_text or not user_text.strip():
                await self.write_event(NotHandled(text="").event())
                return False

            _LOGGER.info("LLM input: %s", user_text)
            self._messages.append({"role": "user", "content": user_text})

            try:
                response_text = await self._client.chat_completion(
                    messages=self._messages,
                    model=self._model,
                    max_tokens=self._max_tokens,
                    stream=False,
                )
                # response_text is str when stream=False
                assert isinstance(response_text, str)
            except Exception:
                _LOGGER.exception("LLM chat-completion failed")
                await self.write_event(
                    NotHandled(text="Sorry, I could not process that.").event()
                )
                return False

            _LOGGER.info("LLM output: %s", response_text)
            self._messages.append(
                {"role": "assistant", "content": response_text}
            )

            await self.write_event(
                Handled(text=response_text).event()
            )
            # Disconnect after one exchange (matches HA pipeline behaviour)
            return False

        return True
