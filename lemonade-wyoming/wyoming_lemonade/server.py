"""Multi-service Wyoming server orchestrator.

Runs three independent ``AsyncTcpServer`` instances — one each for STT,
LLM (conversation), and TTS — so that Home Assistant discovers them as
separate Wyoming services.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any

from wyoming.info import (
    AsrModel,
    AsrProgram,
    Attribution,
    HandleModel,
    HandleProgram,
    Info,
    TtsProgram,
    TtsVoice,
)
from wyoming.server import AsyncServer

from .lemonade_client import LemonadeClient
from .stt_handler import LemonadeSttHandler
from .llm_handler import LemonadeLlmHandler
from .tts_handler import LemonadeTtsHandler

_LOGGER = logging.getLogger(__name__)

_ATTRIBUTION = Attribution(
    name="Lemonade",
    url="https://github.com/rwfsmith/Lemonade-Wyoming",
)


def build_stt_info(model_name: str, language: str) -> Info:
    """Build a Wyoming ``Info`` describing the STT capability."""
    return Info(
        asr=[
            AsrProgram(
                name="lemonade-whisper",
                description="Whisper speech-to-text via Lemonade",
                attribution=_ATTRIBUTION,
                installed=True,
                version="0.1.0",
                models=[
                    AsrModel(
                        name=model_name,
                        description=f"Whisper model: {model_name}",
                        attribution=_ATTRIBUTION,
                        installed=True,
                        version="0.1.0",
                        languages=[language] if language != "auto" else [],
                    )
                ],
            )
        ],
    )


def build_llm_info(model_name: str) -> Info:
    """Build a Wyoming ``Info`` describing the conversation / handle capability."""
    return Info(
        handle=[
            HandleProgram(
                name="lemonade-llm",
                description="LLM conversation agent via Lemonade",
                attribution=_ATTRIBUTION,
                installed=True,
                version="0.1.0",
                models=[
                    HandleModel(
                        name=model_name,
                        description=f"LLM model: {model_name}",
                        attribution=_ATTRIBUTION,
                        installed=True,
                        version="0.1.0",
                        languages=[],
                    )
                ],
            )
        ],
    )


def build_tts_info(model_name: str, voice: str) -> Info:
    """Build a Wyoming ``Info`` describing the TTS capability."""
    return Info(
        tts=[
            TtsProgram(
                name="lemonade-kokoro",
                description="Kokoro text-to-speech via Lemonade",
                attribution=_ATTRIBUTION,
                installed=True,
                version="0.1.0",
                voices=[
                    TtsVoice(
                        name=voice,
                        description=f"Kokoro voice: {voice}",
                        attribution=_ATTRIBUTION,
                        installed=True,
                        version="0.1.0",
                        languages=["en"],
                    )
                ],
            )
        ],
    )


async def run_servers(
    *,
    lemonade_client: LemonadeClient,
    stt_uri: str,
    llm_uri: str,
    tts_uri: str,
    stt_model: str,
    stt_language: str,
    stt_beam_size: int,
    llm_model: str,
    llm_system_prompt: str,
    llm_max_tokens: int,
    tts_model: str,
    tts_voice: str,
    zeroconf: bool = True,
    ready_event: "asyncio.Event | None" = None,
) -> None:
    """Create and run the three Wyoming TCP servers concurrently."""
    # Build Info objects
    stt_info = build_stt_info(stt_model, stt_language)
    llm_info = build_llm_info(llm_model)
    tts_info = build_tts_info(tts_model, tts_voice)

    # Create servers
    stt_server = AsyncServer.from_uri(stt_uri)
    llm_server = AsyncServer.from_uri(llm_uri)
    tts_server = AsyncServer.from_uri(tts_uri)

    _LOGGER.info("Starting Wyoming STT  on %s", stt_uri)
    _LOGGER.info("Starting Wyoming LLM  on %s", llm_uri)
    _LOGGER.info("Starting Wyoming TTS  on %s", tts_uri)

    # Use a real Event; create a pre-set one if caller didn't supply one
    # (pre-set means handlers won't block when run outside HA add-on context)
    if ready_event is None:
        ready_event = asyncio.Event()
        ready_event.set()

    # Handler factories (partial application)
    stt_factory = partial(
        LemonadeSttHandler,
        stt_info,
        lemonade_client,
        stt_model,
        stt_language,
        stt_beam_size,
        ready_event,
    )
    llm_factory = partial(
        LemonadeLlmHandler,
        llm_info,
        lemonade_client,
        llm_model,
        llm_system_prompt,
        llm_max_tokens,
        ready_event,
    )
    tts_factory = partial(
        LemonadeTtsHandler,
        tts_info,
        lemonade_client,
        tts_model,
        tts_voice,
        ready_event,
    )

    # Run all three concurrently
    try:
        await asyncio.gather(
            stt_server.run(stt_factory),
            llm_server.run(llm_factory),
            tts_server.run(tts_factory),
        )
    except asyncio.CancelledError:
        _LOGGER.info("Servers shutting down …")
    finally:
        await lemonade_client.close()
