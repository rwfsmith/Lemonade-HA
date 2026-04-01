"""Self-contained async HTTP client for the Lemonade REST API."""

from __future__ import annotations

import io
import json
import logging
import wave
from typing import Any, AsyncIterator

import httpx

from .const import EP_CHAT_COMPLETIONS, EP_HEALTH, EP_SPEECH, EP_TRANSCRIPTIONS

_LOGGER = logging.getLogger(__name__)


class LemonadeClient:
    """Async wrapper around Lemonade's OpenAI-compatible HTTP API."""

    def __init__(self, host: str, port: int) -> None:
        self._base_url = f"http://{host}:{port}"
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def health_check(self) -> bool:
        try:
            resp = await self._http.get(EP_HEALTH, timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def transcribe(self, wav_bytes: bytes, model: str, language: str = "en") -> str:
        files = {"file": ("audio.wav", io.BytesIO(wav_bytes), "audio/wav")}
        data: dict[str, str] = {"model": model}
        if language and language != "auto":
            data["language"] = language
        resp = await self._http.post(EP_TRANSCRIPTIONS, files=files, data=data, timeout=120.0)
        resp.raise_for_status()
        return resp.json().get("text", "")

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> str:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        resp = await self._http.post(EP_CHAT_COMPLETIONS, json=body, timeout=120.0)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

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
        resp = await self._http.post(EP_SPEECH, json=body, timeout=120.0)
        resp.raise_for_status()
        return resp.content

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
