# Lemonade HA — Local Voice Assist for Home Assistant

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

### 1 — Add this repository to Home Assistant

**Settings → Add-ons → Add-on Store → ⋮ (menu) → Repositories**

Add:
```
https://github.com/rwfsmith/Lemonade-HA
```

### 2 — Install and configure the add-on

1. Find **Lemonade HA** in the store and click **Install**.
2. Open the **Configuration** tab and choose your models and backends.
3. **Start** the add-on. On first launch it will download the selected models
   (this may take a few minutes depending on model size).

On startup the add-on automatically installs the **Lemonade HA** custom
component into your HA config directory.

### 3 — Restart Home Assistant

**Settings → System → Restart** — required once so HA loads the custom component.

### 4 — Add the integration

**Settings → Devices & Services → Add Integration → search "Lemonade HA"**

1. Enter the **host** and **port** of your Lemonade server (default `localhost:8000`).
   HA will verify the connection before proceeding.
2. Choose your STT, LLM, and TTS models.
3. Click **Submit**. The integration registers:
   - **Lemonade Whisper** — Speech-to-Text engine
   - **Lemonade Kokoro** — Text-to-Speech engine
   - **Lemonade LLM** — Conversation agent

### 5 — Create a Voice Assistant

**Settings → Voice Assistants → Add Assistant**

| Field | Value |
|---|---|
| Conversation agent | Lemonade LLM |
| Speech-to-text | Lemonade Whisper |
| Text-to-speech | Lemonade Kokoro |

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
