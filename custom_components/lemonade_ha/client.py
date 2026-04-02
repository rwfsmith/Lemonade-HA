"""Async HTTP client for the Lemonade REST API using aiohttp (bundled with HA)."""

from __future__ import annotations

import aiohttp
import io
import json
import logging
import re
import wave
from typing import Any

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

from .const import EP_CHAT_COMPLETIONS, EP_HEALTH, EP_MODELS, EP_SPEECH, EP_TRANSCRIPTIONS

_LOGGER = logging.getLogger(__name__)

_CONNECT_TIMEOUT = aiohttp.ClientTimeout(total=10)
_READ_TIMEOUT = aiohttp.ClientTimeout(total=300)


class LemonadeClient:
    """Async wrapper around Lemonade's OpenAI-compatible HTTP API."""

    def __init__(self, host: str, port: int) -> None:
        self._base_url = f"http://{host}:{port}"
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(base_url=self._base_url)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def health_check(self) -> bool:
        try:
            session = self._get_session()
            async with session.get(EP_HEALTH, timeout=_CONNECT_TIMEOUT) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def get_models(self) -> list[str]:
        """Return list of model IDs available on the server."""
        try:
            session = self._get_session()
            async with session.get(EP_MODELS, timeout=_CONNECT_TIMEOUT) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    async def transcribe(self, wav_bytes: bytes, model: str, language: str = "en") -> str:
        data = aiohttp.FormData()
        data.add_field("file", io.BytesIO(wav_bytes), filename="audio.wav", content_type="audio/wav")
        data.add_field("model", model)
        if language and language != "auto":
            data.add_field("language", language)
        session = self._get_session()
        async with session.post(EP_TRANSCRIPTIONS, data=data, timeout=_READ_TIMEOUT) as resp:
            resp.raise_for_status()
            result = await resp.json()
            return result.get("text", "")

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> str:
        # Qwen3 models default to thinking mode. The API-level enable_thinking
        # flag is only honoured by vLLM/SGLang. For llama.cpp-based servers
        # (like Lemonade) the reliable way to disable thinking is the soft-switch:
        # append /no_think to the system message.
        patched = list(messages)
        if "qwen3" in model.lower():
            for i, msg in enumerate(patched):
                if msg["role"] == "system":
                    if "/no_think" not in msg["content"] and "/think" not in msg["content"]:
                        patched[i] = {**msg, "content": msg["content"] + " /no_think"}
                    break
            else:
                # No system message present — insert one
                patched = [{"role": "system", "content": "/no_think"}] + patched

        body: dict[str, Any] = {
            "model": model,
            "messages": patched,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        session = self._get_session()
        chunks: list[str] = []
        async with session.post(EP_CHAT_COMPLETIONS, json=body, timeout=_READ_TIMEOUT) as resp:
            resp.raise_for_status()
            async for raw_line in resp.content:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                    delta = data["choices"][0].get("delta", {})
                    token = delta.get("content") or ""
                    if token:
                        chunks.append(token)
                except Exception:
                    continue
        content = "".join(chunks)
        # Strip any residual <think>…</think> blocks (safety net)
        return _THINK_RE.sub("", content).strip()

    async def synthesize_speech(
        self, text: str, model: str = "kokoro-v1", voice: str = "af_heart"
    ) -> bytes:
        """Return raw PCM bytes (24 kHz / 16-bit / mono)."""
        body: dict[str, Any] = {
            "input": text,
            "model": model,
            "voice": voice,
            "response_format": "pcm",
        }
        session = self._get_session()
        async with session.post(EP_SPEECH, json=body, timeout=_READ_TIMEOUT) as resp:
            resp.raise_for_status()
            return await resp.read()

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def pcm_to_wav(
        pcm: bytes,
        sample_rate: int,
        sample_width: int,
        channels: int,
    ) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)
        return buf.getvalue()
