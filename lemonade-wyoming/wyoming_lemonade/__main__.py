"""Entry-point for ``python -m wyoming_lemonade``.

Parses CLI arguments (or reads them from environment / HA add-on options),
ensures Lemonade is running, pulls & loads models, and starts the three
Wyoming servers.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import subprocess
import time

from .const import (
    DEFAULT_LEMONADE_HOST,
    DEFAULT_LEMONADE_PORT,
    DEFAULT_LLM_PORT,
    DEFAULT_STT_PORT,
    DEFAULT_TTS_PORT,
    LEMONADE_HEALTH_POLL_INTERVAL,
    LEMONADE_STARTUP_TIMEOUT,
)
from .lemonade_client import LemonadeClient
from .models import ModelSpec, ensure_all_models_ready
from .server import run_servers

_LOGGER = logging.getLogger("wyoming_lemonade")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wyoming_lemonade",
        description="Wyoming protocol server backed by the Lemonade local-AI platform.",
    )

    # ── STT ──────────────────────────────────────────────────────────────
    g = p.add_argument_group("Speech-to-Text (Whisper)")
    g.add_argument("--stt-model", default="Whisper-Large-v3-Turbo")
    g.add_argument("--stt-backend", default="auto",
                    help="whispercpp:cpu | whispercpp:npu | whispercpp:vulkan | flm:npu | auto")
    g.add_argument("--stt-language", default="en")
    g.add_argument("--stt-beam-size", type=int, default=0)
    g.add_argument("--stt-uri", default=f"tcp://0.0.0.0:{DEFAULT_STT_PORT}")

    # ── LLM ──────────────────────────────────────────────────────────────
    g = p.add_argument_group("LLM / Conversation")
    g.add_argument("--llm-model", default="Qwen3-4B-GGUF")
    g.add_argument("--llm-backend", default="auto",
                    help="llamacpp:vulkan | llamacpp:rocm | llamacpp:cpu | flm:npu | ryzenai:npu | auto")
    g.add_argument("--llm-context-size", type=int, default=4096)
    g.add_argument("--llm-max-tokens", type=int, default=256)
    g.add_argument("--llm-system-prompt", default="")
    g.add_argument("--llm-uri", default=f"tcp://0.0.0.0:{DEFAULT_LLM_PORT}")

    # ── TTS ──────────────────────────────────────────────────────────────
    g = p.add_argument_group("Text-to-Speech (Kokoro)")
    g.add_argument("--tts-model", default="kokoro-v1")
    g.add_argument("--tts-voice", default="af_heart")
    g.add_argument("--tts-uri", default=f"tcp://0.0.0.0:{DEFAULT_TTS_PORT}")

    # ── Lemonade connection ──────────────────────────────────────────────
    g = p.add_argument_group("Lemonade server")
    g.add_argument("--lemonade-host", default=DEFAULT_LEMONADE_HOST)
    g.add_argument("--lemonade-port", type=int, default=DEFAULT_LEMONADE_PORT)
    g.add_argument(
        "--auto-start-lemonade",
        action="store_true",
        default=False,
        help="Try to start lemond if it isn't already running.",
    )

    # ── General ──────────────────────────────────────────────────────────
    p.add_argument("--zeroconf", action="store_true", default=False,
                    help="Register Wyoming services via Zeroconf/mDNS.")
    p.add_argument("--debug", action="store_true", default=False)

    return p


# ── Lemonade lifecycle helpers ───────────────────────────────────────────────

async def _wait_for_lemonade(client: LemonadeClient, timeout: float) -> bool:
    """Poll the Lemonade health endpoint until it responds or we time out."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await client.health_check():
            return True
        _LOGGER.debug("Waiting for Lemonade …")
        await asyncio.sleep(LEMONADE_HEALTH_POLL_INTERVAL)
    return False


def _try_start_lemonade() -> bool:
    """Attempt to launch ``lemond`` as a background process.

    Returns *True* if we launched something (doesn't guarantee it's healthy
    yet).  Works on both Windows (``LemonadeServer.exe`` / ``lemond.exe``)
    and Linux (``lemond``).
    """
    for binary in ("lemond", "LemonadeServer", "lemonade-server"):
        path = shutil.which(binary)
        if path:
            _LOGGER.info("Starting Lemonade via %s", path)
            subprocess.Popen(
                [path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True
    _LOGGER.error(
        "Could not find lemond / LemonadeServer on PATH.  "
        "Please start Lemonade manually or install it."
    )
    return False


# ── Main ─────────────────────────────────────────────────────────────────────

async def _async_main(args: argparse.Namespace) -> None:
    client = LemonadeClient(host=args.lemonade_host, port=args.lemonade_port)

    # Signals handlers that Lemonade is up and models are loaded.
    # Set in the background setup task; handlers await it before processing.
    ready_event = asyncio.Event()

    # Build model specs up front so the background task can capture them.
    stt_spec = ModelSpec(
        name=args.stt_model,
        backend=args.stt_backend,
        extra_load_kwargs=(
            {"whispercpp_args": f"--beam-size {args.stt_beam_size}"}
            if args.stt_beam_size > 0
            else {}
        ),
    )
    llm_spec = ModelSpec(
        name=args.llm_model,
        backend=args.llm_backend,
        extra_load_kwargs={"ctx_size": args.llm_context_size},
    )
    tts_spec = ModelSpec(
        name=args.tts_model,
        backend="auto",
        extra_load_kwargs={},
    )

    async def _setup() -> None:
        """Wait for Lemonade and ensure models are ready, then unblock handlers."""
        # 1. Ensure Lemonade is reachable
        healthy = await client.health_check()
        if not healthy and args.auto_start_lemonade:
            _LOGGER.info("Lemonade not reachable — attempting to start …")
            launched = _try_start_lemonade()
            if launched:
                healthy = await _wait_for_lemonade(
                    client, LEMONADE_STARTUP_TIMEOUT
                )
        if not healthy:
            _LOGGER.warning(
                "Lemonade not responding at http://%s:%d — "
                "will retry for %d s before giving up.",
                args.lemonade_host,
                args.lemonade_port,
                LEMONADE_STARTUP_TIMEOUT,
            )
            healthy = await _wait_for_lemonade(
                client, LEMONADE_STARTUP_TIMEOUT
            )
        if not healthy:
            _LOGGER.error(
                "Cannot reach Lemonade at http://%s:%d.  "
                "Voice requests will fail until Lemonade is available.",
                args.lemonade_host,
                args.lemonade_port,
            )
            # Do not exit — keep servers alive so HA doesn't restart the add-on.
            # When Lemonade eventually becomes available the handlers will log
            # an error and HA can retry.
            return

        _LOGGER.info(
            "Lemonade is healthy at http://%s:%d",
            args.lemonade_host,
            args.lemonade_port,
        )

        # 2. Download & load models
        await ensure_all_models_ready(client, stt_spec, llm_spec, tts_spec)

        # 3. Unblock all waiting handlers
        ready_event.set()
        _LOGGER.info("Lemonade-Wyoming is ready to handle voice requests.")

    # Kick off setup in the background — Wyoming servers open their ports first
    # so HA Supervisor considers the add-on started within its timeout window.
    asyncio.create_task(_setup())

    # 3. Start Wyoming servers (opens TCP ports immediately)
    await run_servers(
        lemonade_client=client,
        stt_uri=args.stt_uri,
        llm_uri=args.llm_uri,
        tts_uri=args.tts_uri,
        stt_model=args.stt_model,
        stt_language=args.stt_language,
        stt_beam_size=args.stt_beam_size,
        llm_model=args.llm_model,
        llm_system_prompt=args.llm_system_prompt,
        llm_max_tokens=args.llm_max_tokens,
        tts_model=args.tts_model,
        tts_voice=args.tts_voice,
        zeroconf=args.zeroconf,
        ready_event=ready_event,
    )


def run() -> None:
    """CLI entry-point."""
    parser = _build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    asyncio.run(_async_main(args))


if __name__ == "__main__":
    run()
