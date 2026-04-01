"""Model management — list, download, and load models via Lemonade."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from .const import BACKEND_LOAD_KWARGS
from .lemonade_client import LemonadeClient

_LOGGER = logging.getLogger(__name__)


@dataclass
class ModelSpec:
    """Parameters needed to ensure a single model is ready."""

    name: str
    backend: str  # e.g. "auto", "llamacpp:vulkan", "whispercpp:npu"
    extra_load_kwargs: dict[str, Any]


def _resolve_backend_kwargs(backend: str) -> dict[str, Any]:
    """Convert user-facing backend string to Lemonade ``/load`` kwargs."""
    if backend == "auto" or not backend:
        return {}
    return dict(BACKEND_LOAD_KWARGS.get(backend, {}))


async def ensure_model_ready(
    client: LemonadeClient,
    spec: ModelSpec,
) -> None:
    """Make sure *spec.name* is downloaded and loaded in Lemonade."""
    name = spec.name
    # 1. Download if necessary
    downloaded = await client.is_model_downloaded(name)
    if not downloaded:
        _LOGGER.info("Model %s is not yet downloaded — pulling …", name)
        await client.pull_model(name)
    else:
        _LOGGER.debug("Model %s already downloaded.", name)

    # 2. Load with the right backend / options
    load_kw = _resolve_backend_kwargs(spec.backend)
    load_kw.update(spec.extra_load_kwargs)
    try:
        await client.load_model(name, **load_kw)
    except Exception:
        _LOGGER.exception("Failed to load model %s", name)
        raise


async def ensure_all_models_ready(
    client: LemonadeClient,
    stt: ModelSpec,
    llm: ModelSpec,
    tts: ModelSpec,
) -> None:
    """Download (if needed) and load all three capability models.

    Downloads run sequentially (to avoid bandwidth fights), but the loads
    could happen in any order — Lemonade keeps one model per backend type
    (audio / llm / tts) so all three can coexist.
    """
    for spec in (stt, llm, tts):
        await ensure_model_ready(client, spec)
    _LOGGER.info(
        "All models ready — STT=%s  LLM=%s  TTS=%s",
        stt.name,
        llm.name,
        tts.name,
    )


async def list_available_models(
    client: LemonadeClient,
    label_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Return models from Lemonade's registry, optionally filtered by label.

    *label_filter* can be ``"audio"``, ``"llm"``, ``"tts"`` etc.
    """
    models = await client.list_models(show_all=True)
    if not label_filter:
        return models
    return [
        m
        for m in models
        if label_filter in (m.get("labels") or [])
        or label_filter in (m.get("id", "") + m.get("name", "")).lower()
    ]
