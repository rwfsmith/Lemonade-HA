"""Async HTTP client for the Lemonade local-AI server.

Wraps every Lemonade REST endpoint that the Wyoming handlers need:
health, models, pull, load, unload, transcribe, chat, and synthesize.
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any, AsyncIterator

import httpx

from .const import (
    EP_CHAT_COMPLETIONS,
    EP_HEALTH,
    EP_LOAD,
    EP_MODELS,
    EP_PULL,
    EP_SPEECH,
    EP_TRANSCRIPTIONS,
    EP_UNLOAD,
    MODEL_PULL_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class LemonadeClient:
    """Thin async wrapper around the Lemonade OpenAI-compatible HTTP API."""

    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        self.base_url = f"http://{host}:{port}"
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
        )

    # ── lifecycle ────────────────────────────────────────────────────────

    async def close(self) -> None:
        await self._client.aclose()

    # ── health ───────────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Return *True* if the Lemonade server is reachable and healthy."""
        try:
            resp = await self._client.get(EP_HEALTH, timeout=5.0)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, OSError):
            return False

    # ── models ───────────────────────────────────────────────────────────

    async def list_models(self, *, show_all: bool = False) -> list[dict[str, Any]]:
        """Return the list of models known to Lemonade.

        With *show_all=True* the full registry (including not-yet-downloaded
        models) is returned.
        """
        params: dict[str, Any] = {}
        if show_all:
            params["show_all"] = "true"
        resp = await self._client.get(EP_MODELS, params=params)
        resp.raise_for_status()
        body = resp.json()
        # The OpenAI /v1/models endpoint returns {"data": [...]}
        return body.get("data", body) if isinstance(body, dict) else body

    async def is_model_downloaded(self, model_name: str) -> bool:
        """Check whether *model_name* has already been downloaded."""
        models = await self.list_models(show_all=True)
        for m in models:
            mid = m.get("id") or m.get("name", "")
            if mid == model_name:
                return m.get("downloaded", m.get("installed", False))
        # If we can't find it in the registry, assume not downloaded
        return False

    async def pull_model(self, model_name: str) -> None:
        """Download *model_name* from Hugging Face Hub via Lemonade.

        Streams SSE progress events and logs them.
        """
        _LOGGER.info("Pulling model %s …", model_name)
        async with self._client.stream(
            "POST",
            EP_PULL,
            json={"model_name": model_name, "stream": True},
            timeout=MODEL_PULL_TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                payload = line.removeprefix("data:").strip()
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                    status = data.get("status", "")
                    pct = data.get("percent", "")
                    if pct:
                        _LOGGER.debug("  %s: %s%%", model_name, pct)
                    elif status:
                        _LOGGER.info("  %s: %s", model_name, status)
                except json.JSONDecodeError:
                    pass
        _LOGGER.info("Model %s downloaded.", model_name)

    async def load_model(
        self, model_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Load a model into memory.

        Extra *kwargs* are merged into the JSON body (e.g.
        ``llamacpp_backend="vulkan"``, ``ctx_size=4096``).
        """
        body: dict[str, Any] = {"model_name": model_name}
        body.update(kwargs)
        _LOGGER.info("Loading model %s  kwargs=%s", model_name, kwargs)
        resp = await self._client.post(EP_LOAD, json=body, timeout=120.0)
        resp.raise_for_status()
        return resp.json()

    async def unload_model(self, model_name: str) -> None:
        """Unload a previously loaded model."""
        resp = await self._client.post(
            EP_UNLOAD, json={"model_name": model_name}, timeout=30.0
        )
        resp.raise_for_status()

    # ── STT (Whisper) ────────────────────────────────────────────────────

    async def transcribe(
        self,
        wav_bytes: bytes,
        model: str,
        language: str = "en",
    ) -> str:
        """Send a WAV file to Lemonade and return the transcribed text."""
        files = {"file": ("audio.wav", io.BytesIO(wav_bytes), "audio/wav")}
        data: dict[str, str] = {"model": model}
        if language and language != "auto":
            data["language"] = language

        resp = await self._client.post(
            EP_TRANSCRIPTIONS,
            files=files,
            data=data,
            timeout=120.0,
        )
        resp.raise_for_status()
        result = resp.json()
        return result.get("text", "")

    # ── LLM (chat completions) ───────────────────────────────────────────

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        *,
        max_tokens: int = 256,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """Send a chat-completion request.

        When *stream=False* the full assistant message is returned as a str.
        When *stream=True* an async iterator of text deltas is returned.
        """
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        if not stream:
            resp = await self._client.post(
                EP_CHAT_COMPLETIONS, json=body, timeout=120.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

        # Streaming — return an async generator
        return self._stream_chat(body)

    async def _stream_chat(self, body: dict[str, Any]) -> AsyncIterator[str]:
        """Yield text deltas from an SSE chat-completion stream."""
        async with self._client.stream(
            "POST", EP_CHAT_COMPLETIONS, json=body, timeout=120.0
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                payload = line.removeprefix("data:").strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = (
                        chunk.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content", "")
                    )
                    if delta:
                        yield delta
                except (json.JSONDecodeError, IndexError, KeyError):
                    pass

    # ── TTS (Kokoro) ─────────────────────────────────────────────────────

    async def synthesize_speech(
        self,
        text: str,
        model: str = "kokoro-v1",
        voice: str = "af_heart",
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize *text* and return raw PCM audio bytes (24 kHz s16le mono)."""
        body: dict[str, Any] = {
            "input": text,
            "model": model,
            "voice": voice,
            "speed": speed,
            "response_format": "pcm",
        }
        resp = await self._client.post(EP_SPEECH, json=body, timeout=120.0)
        resp.raise_for_status()
        return resp.content

    async def synthesize_speech_streaming(
        self,
        text: str,
        model: str = "kokoro-v1",
        voice: str = "af_heart",
        speed: float = 1.0,
        chunk_size: int = 4800,
    ) -> AsyncIterator[bytes]:
        """Stream raw PCM audio chunks for *text*.

        *chunk_size* is in **bytes** (4800 B ≈ 100 ms at 24 kHz/16-bit/mono).
        """
        body: dict[str, Any] = {
            "input": text,
            "model": model,
            "voice": voice,
            "speed": speed,
            "response_format": "pcm",
            "stream_format": "audio",
        }
        async with self._client.stream(
            "POST", EP_SPEECH, json=body, timeout=120.0
        ) as resp:
            resp.raise_for_status()
            async for raw in resp.aiter_bytes(chunk_size):
                if raw:
                    yield raw
