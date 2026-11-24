# Lemonade HA — Local Voice Assist for Home Assistant

![Lemonade brand icon](icon.png)

> **Transparency notice:** This integration was entirely vibe coded with GitHub Copilot. Use it accordingly.

Run **fully local** voice assistants in Home Assistant using [Lemonade](https://github.com/lemonade-sdk/lemonade) as the AI backend.

| Capability | Backend | Models |
|---|---|---|
| **Speech-to-Text** | Whisper via whisper.cpp or FastFlowLM | Whisper Tiny → Large-v3-Turbo |
| **Conversation / LLM** | LLama.cpp (Vulkan/ROCm/CPU), FastFlowLM (NPU), RyzenAI (NPU) | Qwen 3, Llama 3.2, Phi-4, Mistral 7B, and 100+ more |
| **Text-to-Speech** | Kokoro TTS | kokoro-v1 (multiple voices) |

---

## Prerequisites

1. **Lemonade server** installed and running on your machine.
   Download from <https://github.com/lemonade-sdk/lemonade/releases>.
2. If running Home Assistant OS or Supervised, Lemonade should run on the
   **host** (not inside a container). Set the host to `homeassistant.local`
   or the host's LAN IP.

---

## Installation

### Method A — HACS (recommended)

The integration can be installed and updated directly through HACS, with no add-on required.

1. In HACS, click **⋮ → Custom repositories**, paste `https://github.com/rwfsmith/Lemonade-HA`, choose category **Integration**, and click **Add**.
2. Search for **Lemonade HA** and click **Download**.
3. **Restart Home Assistant** so HA loads the custom component.
4. Proceed to [Add the integration](#add-the-integration) below.

To update: HACS will notify you when a new version is available — click **Update** and restart HA.

---

### Method B — Add-on (auto-installs the integration)

The add-on bundles the integration and copies it into your HA config directory on startup.
Use this method if you prefer not to use HACS.

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, add:
   ```
   https://github.com/rwfsmith/Lemonade-HA
   ```
2. Find **Lemonade HA**, click **Install**, then **Start**.
3. **Restart Home Assistant** once so HA loads the custom component.

> **Tip:** If you later switch to HACS-managed updates, set `copy_integration: false` in the add-on
> Configuration tab. The add-on will no longer overwrite the component on restart, so HACS controls
> the integration version independently.

---

### Add the integration

**Settings → Devices & Services → Add Integration → search "Lemonade HA"**

1. Enter the **host** and **port** of your Lemonade server (default `localhost:8000`).
   HA will verify the connection before proceeding.
2. Choose your STT, LLM, and TTS models.
3. Click **Submit**. The integration registers:
   - **Lemonade Whisper** — Speech-to-Text engine
   - **Lemonade Kokoro** — Text-to-Speech engine
   - **Lemonade LLM** — Conversation agent

### Create a Voice Assistant

**Settings → Voice Assistants → Add Assistant**

| Field | Value |
|---|---|
| Conversation agent | Lemonade LLM |
| Speech-to-text | Lemonade Whisper |
| Text-to-speech | Lemonade Kokoro |

### Continue without the wake word

In **Settings → Devices & Services → Lemonade HA**, edit the LLM conversation
agent and turn on **Continue without the wake word**. It is off by default and
requires Home Assistant 2025.4 or later and a client that supports Assist
continuation. If **Prefer handling commands locally** is enabled in your voice
assistant, turns handled entirely by Home Assistant do not use this setting.

For a custom device using the [Assist pipeline WebSocket API](https://developers.home-assistant.io/docs/voice/pipelines/):

1. Start the first run as usual, without a `conversation_id` for a new chat.
2. Read `continue_conversation` and `conversation_id` from
   `intent-end.data.intent_output`. If the flag is `true`, wait for the current
   run and audio playback to finish, then start a new `assist_pipeline/run`
   with `start_stage: "stt"`, `end_stage: "tts"`, and the returned
   `conversation_id` as a top-level field. Reuse the same pipeline.
3. Return to wake-word mode and discard the ID if the flag is false or absent,
   the run fails, the user cancels, or nobody speaks within the client's
   follow-up timeout. In English, **“stop listening”** or **“end conversation”**
   also ends the exchange.

### Spoken replies

Lemonade instructs conversation models to use plain spoken text, including when
you have saved a custom system prompt. Markdown emphasis, headings, list markers,
link markup, and emoji are also removed from replies before Home Assistant sends
them to your selected TTS engine. Follow-up history uses the cleaned replies.
This does not change text sent directly to the TTS service outside conversation.

### LLM reasoning effort

When adding or editing an LLM conversation service under **Settings → Devices & Services
→ Lemonade HA**, choose **Reasoning effort**: `minimal`, `low`, `medium`, `high`,
`xhigh`, or `max`. New services default to `minimal`. The selection is sent as
`reasoning_effort` on every chat completion, including tool-call follow-ups.
Support and the effect of each level depend on the Lemonade backend and model;
unsupported levels may be ignored or rejected by the server. Higher efforts may
need a larger **Max response tokens** budget.

Existing services keep their previous behavior until edited and saved. Selecting
an effort stops the integration from forcing Qwen3's `/no_think` mode; explicit
`/think` or `/no_think` instructions in your own system prompt are left untouched.

The bundled integration brand icon requires **Home Assistant 2026.3 or newer**.
The integration and add-on reuse the [Lemonade SDK icon](https://github.com/lemonade-sdk/lemonade/blob/f7077fcfb1b73752a2f380aaace614192a3a0e34/docs/assets/logo_512.png),
Copyright 2026 Lemonade Community, under [Apache-2.0](custom_components/lemonade_ha/brand/LICENSE).
The 256-pixel icons are resized copies of the upstream 512-pixel image.

---

## Add-on Configuration Options

### Speech-to-Text

| Option | Default | Description |
|---|---|---|
| STT Model | `Whisper-Large-v3-Turbo` | Whisper model size. Larger = more accurate, slower. |
| STT Backend | `auto` | `whispercpp:cpu`, `whispercpp:npu`, `whispercpp:vulkan`, or `flm:npu` |
| STT Language | `en` | ISO 639-1 code or `auto` for language detection |
| STT Beam Size | `0` | Beam search width (`0` = auto) |

### Conversation / LLM

| Option | Default | Description |
|---|---|---|
| LLM Backend | `llamacpp` | `llamacpp`, `ryzenai`, or `flm` |
| LLM Model | `Qwen3-4B-GGUF` | Model name for the selected backend |
| LLM Context Size | `4096` | Max context window in tokens |
| LLM Max Tokens | `256` | Max tokens per response |
| LLM System Prompt | *(built-in)* | Customise the assistant personality |

### Text-to-Speech

| Option | Default | Description |
|---|---|---|
| TTS Model | `kokoro-v1` | Kokoro ONNX model |
| TTS Voice | `af_heart` | Voice ID (`af_` = American Female, `am_` = American Male, `bf_` = British Female, `bm_` = British Male) |

### Connection

| Option | Default | Description |
|---|---|---|
| Lemonade Host | `localhost` | Hostname or IP of the Lemonade server |
| Lemonade Port | `8000` | HTTP port of the Lemonade server |
| Auto-start Lemonade | `false` | Try to launch `lemond` if not already running |

---

## Supported Hardware

| Hardware | Recommended Backend |
|---|---|
| AMD Ryzen AI (NPU) | `ryzenai` (LLM), `flm:npu` (STT) |
| AMD GPU (Radeon) | `llamacpp` + `vulkan` sub-backend |
| CPU only | `llamacpp` + `cpu` sub-backend |
| Apple Silicon | `llamacpp` + `metal` sub-backend |

---

## Troubleshooting

**Add-on starts but integration doesn't appear after HA restart**
→ Check that the add-on started successfully and that `/config/custom_components/lemonade_wyoming/` exists. Restart HA again if needed.

**"Cannot connect" error when adding integration**
→ Verify Lemonade is running (`curl http://localhost:8000/api/v1/health`). If HA OS, use the host LAN IP instead of `localhost`.

**Models not downloading**
→ Check the add-on log (**Add-ons → Lemonade HA → Log**). Model downloads can take several minutes.

---

## Links

- [Lemonade SDK](https://github.com/lemonade-sdk/lemonade)
- [Wyoming Protocol](https://github.com/rhasspy/wyoming)
- [Home Assistant Voice](https://www.home-assistant.io/voice_control/)
