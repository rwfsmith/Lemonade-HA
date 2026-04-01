"""Constants and defaults for wyoming-lemonade."""

from __future__ import annotations

# ── Default ports ────────────────────────────────────────────────────────────
DEFAULT_STT_PORT = 10500
DEFAULT_LLM_PORT = 10600
DEFAULT_TTS_PORT = 10700
DEFAULT_LEMONADE_PORT = 8000
DEFAULT_LEMONADE_HOST = "localhost"

# ── Lemonade API paths ──────────────────────────────────────────────────────
API_PREFIX = "/api/v1"
EP_HEALTH = f"{API_PREFIX}/health"
EP_MODELS = f"{API_PREFIX}/models"
EP_PULL = f"{API_PREFIX}/pull"
EP_LOAD = f"{API_PREFIX}/load"
EP_UNLOAD = f"{API_PREFIX}/unload"
EP_TRANSCRIPTIONS = f"{API_PREFIX}/audio/transcriptions"
EP_CHAT_COMPLETIONS = f"{API_PREFIX}/chat/completions"
EP_SPEECH = f"{API_PREFIX}/audio/speech"

# ── Audio defaults ───────────────────────────────────────────────────────────
WHISPER_SAMPLE_RATE = 16000  # Hz – what Whisper expects
WHISPER_SAMPLE_WIDTH = 2  # 16-bit PCM
WHISPER_CHANNELS = 1  # mono

KOKORO_SAMPLE_RATE = 24000  # Hz – Kokoro's native output rate
KOKORO_SAMPLE_WIDTH = 2  # 16-bit PCM
KOKORO_CHANNELS = 1  # mono

# ── Model registries (curated defaults) ──────────────────────────────────────
STT_MODELS: dict[str, dict] = {
    "Whisper-Tiny": {"size_gb": 0.075, "recipe": "whispercpp"},
    "Whisper-Base": {"size_gb": 0.142, "recipe": "whispercpp"},
    "Whisper-Small": {"size_gb": 0.466, "recipe": "whispercpp"},
    "Whisper-Medium": {"size_gb": 1.42, "recipe": "whispercpp"},
    "Whisper-Large-v3": {"size_gb": 2.87, "recipe": "whispercpp"},
    "Whisper-Large-v3-Turbo": {"size_gb": 1.55, "recipe": "whispercpp"},
}

LLM_MODELS: dict[str, dict] = {
    # llamacpp (GGUF)
    "Cogito-v2-llama-109B-MoE-GGUF": {"size_gb": 65.3, "recipe": "llamacpp"},
    "DeepSeek-Qwen3-8B-GGUF": {"size_gb": 5.25, "recipe": "llamacpp"},
    "Devstral-Small-2507-GGUF": {"size_gb": 14.3, "recipe": "llamacpp"},
    "GLM-4.5-Air-UD-Q4K-XL-GGUF": {"size_gb": 73.1, "recipe": "llamacpp"},
    "GLM-4.7-Flash-GGUF": {"size_gb": 17.6, "recipe": "llamacpp"},
    "Gemma-3-4b-it-GGUF": {"size_gb": 3.61, "recipe": "llamacpp"},
    "Jan-nano-128k-GGUF": {"size_gb": 2.5, "recipe": "llamacpp"},
    "Jan-v1-4B-GGUF": {"size_gb": 2.5, "recipe": "llamacpp"},
    "LFM2-1.2B-GGUF": {"size_gb": 0.731, "recipe": "llamacpp"},
    "LFM2-24B-A2B-GGUF": {"size_gb": 14.4, "recipe": "llamacpp"},
    "LFM2-8B-A1B-GGUF": {"size_gb": 4.8, "recipe": "llamacpp"},
    "LFM2.5-1.2B-Instruct-GGUF": {"size_gb": 0.731, "recipe": "llamacpp"},
    "Llama-3.2-1B-Instruct-GGUF": {"size_gb": 0.834, "recipe": "llamacpp"},
    "Llama-3.2-3B-Instruct-GGUF": {"size_gb": 2.06, "recipe": "llamacpp"},
    "Llama-4-Scout-17B-16E-Instruct-GGUF": {"size_gb": 61.5, "recipe": "llamacpp"},
    "Ministral-3-3B-Instruct-2512-GGUF": {"size_gb": 2.85, "recipe": "llamacpp"},
    "Nemotron-3-Nano-30B-A3B-GGUF": {"size_gb": 22.8, "recipe": "llamacpp"},
    "Phi-4-mini-instruct-GGUF": {"size_gb": 2.49, "recipe": "llamacpp"},
    "Playable1-GGUF": {"size_gb": 4.68, "recipe": "llamacpp"},
    "PromptBridge-0.6b-Alpha-GGUF": {"size_gb": 0.397, "recipe": "llamacpp"},
    "Qwen2.5-Coder-32B-Instruct-GGUF": {"size_gb": 19.85, "recipe": "llamacpp"},
    "Qwen2.5-VL-3B-Instruct-GGUF": {"size_gb": 3.27, "recipe": "llamacpp"},
    "Qwen2.5-VL-7B-Instruct-GGUF": {"size_gb": 4.68, "recipe": "llamacpp"},
    "Qwen3-0.6B-GGUF": {"size_gb": 0.38, "recipe": "llamacpp"},
    "Qwen3-1.7B-GGUF": {"size_gb": 1.06, "recipe": "llamacpp"},
    "Qwen3-4B-GGUF": {"size_gb": 2.38, "recipe": "llamacpp"},
    "Qwen3-4B-Instruct-2507-GGUF": {"size_gb": 2.5, "recipe": "llamacpp"},
    "Qwen3-8B-GGUF": {"size_gb": 5.25, "recipe": "llamacpp"},
    "Qwen3-14B-GGUF": {"size_gb": 8.54, "recipe": "llamacpp"},
    "Qwen3-30B-A3B-GGUF": {"size_gb": 17.4, "recipe": "llamacpp"},
    "Qwen3-30B-A3B-Instruct-2507-GGUF": {"size_gb": 17.4, "recipe": "llamacpp"},
    "Qwen3-Coder-30B-A3B-Instruct-GGUF": {"size_gb": 18.6, "recipe": "llamacpp"},
    "Qwen3-Coder-Next-GGUF": {"size_gb": 43.7, "recipe": "llamacpp"},
    "Qwen3-Next-80B-A3B-Instruct-GGUF": {"size_gb": 45.1, "recipe": "llamacpp"},
    "Qwen3-VL-4B-Instruct-GGUF": {"size_gb": 3.33, "recipe": "llamacpp"},
    "Qwen3-VL-8B-Instruct-GGUF": {"size_gb": 6.19, "recipe": "llamacpp"},
    "Qwen3.5-0.8B-GGUF": {"size_gb": 0.56, "recipe": "llamacpp"},
    "Qwen3.5-2B-GGUF": {"size_gb": 1.34, "recipe": "llamacpp"},
    "Qwen3.5-4B-GGUF": {"size_gb": 2.91, "recipe": "llamacpp"},
    "Qwen3.5-9B-GGUF": {"size_gb": 5.97, "recipe": "llamacpp"},
    "Qwen3.5-27B-GGUF": {"size_gb": 16.7, "recipe": "llamacpp"},
    "Qwen3.5-35B-A3B-GGUF": {"size_gb": 19.7, "recipe": "llamacpp"},
    "Qwen3.5-122B-A10B-GGUF": {"size_gb": 68.4, "recipe": "llamacpp"},
    "SmolLM3-3B-GGUF": {"size_gb": 1.94, "recipe": "llamacpp"},
    "gpt-oss-20b-GGUF": {"size_gb": 11.6, "recipe": "llamacpp"},
    "gpt-oss-20b-mxfp4-GGUF": {"size_gb": 12.1, "recipe": "llamacpp"},
    "gpt-oss-120b-GGUF": {"size_gb": 62.7, "recipe": "llamacpp"},
    "gpt-oss-120b-mxfp-GGUF": {"size_gb": 63.3, "recipe": "llamacpp"},
    "granite-4.0-h-tiny-GGUF": {"size_gb": 4.25, "recipe": "llamacpp"},
    # ryzenai-llm (ONNX Hybrid/NPU/CPU)
    "AMD-OLMo-1B-SFT-DPO-Hybrid": {"size_gb": 1.38, "recipe": "ryzenai-llm"},
    "CodeLlama-7b-Instruct-hf-Hybrid": {"size_gb": 6.74, "recipe": "ryzenai-llm"},
    "CodeLlama-7b-Instruct-hf-NPU": {"size_gb": 7.03, "recipe": "ryzenai-llm"},
    "DeepSeek-R1-Distill-Llama-8B-CPU": {"size_gb": 5.78, "recipe": "ryzenai-llm"},
    "DeepSeek-R1-Distill-Llama-8B-Hybrid": {"size_gb": 8.47, "recipe": "ryzenai-llm"},
    "DeepSeek-R1-Distill-Llama-8B-NPU": {"size_gb": 8.66, "recipe": "ryzenai-llm"},
    "DeepSeek-R1-Distill-Qwen-1.5B-Hybrid": {"size_gb": 2.04, "recipe": "ryzenai-llm"},
    "DeepSeek-R1-Distill-Qwen-1.5B-NPU": {"size_gb": 2.14, "recipe": "ryzenai-llm"},
    "DeepSeek-R1-Distill-Qwen-7B-CPU": {"size_gb": 5.78, "recipe": "ryzenai-llm"},
    "DeepSeek-R1-Distill-Qwen-7B-Hybrid": {"size_gb": 8.08, "recipe": "ryzenai-llm"},
    "DeepSeek-R1-Distill-Qwen-7B-NPU": {"size_gb": 8.26, "recipe": "ryzenai-llm"},
    "Gemma-3-4b-it-mm-NPU": {"size_gb": 6.22, "recipe": "ryzenai-llm"},
    "Llama-2-7b-chat-hf-Hybrid": {"size_gb": 6.8, "recipe": "ryzenai-llm"},
    "Llama-2-7b-chat-hf-NPU": {"size_gb": 6.95, "recipe": "ryzenai-llm"},
    "Llama-2-7b-hf-Hybrid": {"size_gb": 6.8, "recipe": "ryzenai-llm"},
    "Llama-2-7b-hf-NPU": {"size_gb": 6.95, "recipe": "ryzenai-llm"},
    "Llama-3.1-8B-Hybrid": {"size_gb": 8.47, "recipe": "ryzenai-llm"},
    "Llama-3.1-8B-NPU": {"size_gb": 8.66, "recipe": "ryzenai-llm"},
    "Llama-3.2-1B-Hybrid": {"size_gb": 1.76, "recipe": "ryzenai-llm"},
    "Llama-3.2-1B-Instruct-CPU": {"size_gb": 1.64, "recipe": "ryzenai-llm"},
    "Llama-3.2-1B-Instruct-Hybrid": {"size_gb": 1.76, "recipe": "ryzenai-llm"},
    "Llama-3.2-1B-Instruct-NPU": {"size_gb": 1.82, "recipe": "ryzenai-llm"},
    "Llama-3.2-1B-NPU": {"size_gb": 1.82, "recipe": "ryzenai-llm"},
    "Llama-3.2-3B-Hybrid": {"size_gb": 3.98, "recipe": "ryzenai-llm"},
    "Llama-3.2-3B-Instruct-CPU": {"size_gb": 3.15, "recipe": "ryzenai-llm"},
    "Llama-3.2-3B-Instruct-Hybrid": {"size_gb": 3.98, "recipe": "ryzenai-llm"},
    "Meta-Llama-3-8B-Hybrid": {"size_gb": 8.44, "recipe": "ryzenai-llm"},
    "Meta-Llama-3-8B-NPU": {"size_gb": 8.6, "recipe": "ryzenai-llm"},
    "Meta-Llama-3.1-8B-Instruct-Hybrid": {"size_gb": 8.47, "recipe": "ryzenai-llm"},
    "Meta-Llama-3.1-8B-Instruct-NPU": {"size_gb": 8.66, "recipe": "ryzenai-llm"},
    "Mistral-7B-Instruct-v0.1-Hybrid": {"size_gb": 7.3, "recipe": "ryzenai-llm"},
    "Mistral-7B-Instruct-v0.1-NPU": {"size_gb": 7.46, "recipe": "ryzenai-llm"},
    "Mistral-7B-Instruct-v0.2-Hybrid": {"size_gb": 7.3, "recipe": "ryzenai-llm"},
    "Mistral-7B-Instruct-v0.2-NPU": {"size_gb": 7.46, "recipe": "ryzenai-llm"},
    "Mistral-7B-Instruct-v0.3-Hybrid": {"size_gb": 7.31, "recipe": "ryzenai-llm"},
    "Mistral-7B-Instruct-v0.3-NPU": {"size_gb": 7.54, "recipe": "ryzenai-llm"},
    "Mistral-7B-v0.3-Hybrid": {"size_gb": 7.31, "recipe": "ryzenai-llm"},
    "Mistral-7B-v0.3-NPU": {"size_gb": 7.54, "recipe": "ryzenai-llm"},
    "Phi-3-Mini-Instruct-CPU": {"size_gb": 2.23, "recipe": "ryzenai-llm"},
    "Phi-3-mini-128k-instruct-Hybrid": {"size_gb": 3.92, "recipe": "ryzenai-llm"},
    "Phi-3-mini-128k-instruct-NPU": {"size_gb": 4.05, "recipe": "ryzenai-llm"},
    "Phi-3-mini-4k-instruct-Hybrid": {"size_gb": 3.9, "recipe": "ryzenai-llm"},
    "Phi-3-mini-4k-instruct-NPU": {"size_gb": 4.0, "recipe": "ryzenai-llm"},
    "Phi-3.5-mini-instruct-Hybrid": {"size_gb": 3.92, "recipe": "ryzenai-llm"},
    "Phi-3.5-mini-instruct-NPU": {"size_gb": 4.05, "recipe": "ryzenai-llm"},
    "Phi-4-mini-instruct-Hybrid": {"size_gb": 5.1, "recipe": "ryzenai-llm"},
    "Phi-4-mini-instruct-NPU": {"size_gb": 5.21, "recipe": "ryzenai-llm"},
    "Phi-4-mini-reasoning-Hybrid": {"size_gb": 5.1, "recipe": "ryzenai-llm"},
    "Qwen-1.5-7B-Chat-CPU": {"size_gb": 5.89, "recipe": "ryzenai-llm"},
    "Qwen-2.5-1.5B-Instruct-Hybrid": {"size_gb": 2.02, "recipe": "ryzenai-llm"},
    "Qwen-2.5-1.5B-Instruct-NPU": {"size_gb": 2.1, "recipe": "ryzenai-llm"},
    "Qwen1.5-7B-Chat-Hybrid": {"size_gb": 8.23, "recipe": "ryzenai-llm"},
    "Qwen1.5-7B-Chat-NPU": {"size_gb": 8.4, "recipe": "ryzenai-llm"},
    "Qwen2-1.5B-Hybrid": {"size_gb": 2.04, "recipe": "ryzenai-llm"},
    "Qwen2-1.5B-NPU": {"size_gb": 2.14, "recipe": "ryzenai-llm"},
    "Qwen2-7B-Hybrid": {"size_gb": 8.08, "recipe": "ryzenai-llm"},
    "Qwen2-7B-NPU": {"size_gb": 8.27, "recipe": "ryzenai-llm"},
    "Qwen2.5-0.5B-Instruct-CPU": {"size_gb": 0.77, "recipe": "ryzenai-llm"},
    "Qwen2.5-0.5B-Instruct-Hybrid": {"size_gb": 0.77, "recipe": "ryzenai-llm"},
    "Qwen2.5-3B-Instruct-Hybrid": {"size_gb": 3.7, "recipe": "ryzenai-llm"},
    "Qwen2.5-3B-Instruct-NPU": {"size_gb": 3.81, "recipe": "ryzenai-llm"},
    "Qwen2.5-7B-Instruct-Hybrid": {"size_gb": 8.06, "recipe": "ryzenai-llm"},
    "Qwen2.5-7B-Instruct-NPU": {"size_gb": 8.22, "recipe": "ryzenai-llm"},
    "Qwen2.5-14B-instruct-Hybrid": {"size_gb": 15.31, "recipe": "ryzenai-llm"},
    "Qwen2.5-Coder-0.5B-Instruct-Hybrid": {"size_gb": 0.77, "recipe": "ryzenai-llm"},
    "Qwen2.5-Coder-1.5B-Instruct-Hybrid": {"size_gb": 2.02, "recipe": "ryzenai-llm"},
    "Qwen2.5-Coder-1.5B-Instruct-NPU": {"size_gb": 2.1, "recipe": "ryzenai-llm"},
    "Qwen2.5-Coder-7B-Instruct-Hybrid": {"size_gb": 8.06, "recipe": "ryzenai-llm"},
    "Qwen2.5-Coder-7B-Instruct-NPU": {"size_gb": 8.22, "recipe": "ryzenai-llm"},
    "Qwen3-1.7B-Hybrid": {"size_gb": 2.38, "recipe": "ryzenai-llm"},
    "Qwen3-4B-Hybrid": {"size_gb": 4.82, "recipe": "ryzenai-llm"},
    "Qwen3-8B-Hybrid": {"size_gb": 8.77, "recipe": "ryzenai-llm"},
    "Qwen3-14B-Hybrid": {"size_gb": 15.31, "recipe": "ryzenai-llm"},
    "SmolLM-135M-Instruct-Hybrid": {"size_gb": 0.22, "recipe": "ryzenai-llm"},
    "SmolLM2-135M-Instruct-Hybrid": {"size_gb": 0.22, "recipe": "ryzenai-llm"},
    "chatglm3-6b-Hybrid": {"size_gb": 6.43, "recipe": "ryzenai-llm"},
    "chatglm3-6b-NPU": {"size_gb": 6.55, "recipe": "ryzenai-llm"},
    "gemma-2-2b-Hybrid": {"size_gb": 3.76, "recipe": "ryzenai-llm"},
    "gpt-oss-20b-NPU": {"size_gb": 12.49, "recipe": "ryzenai-llm"},
    # flm (FastFlowLM NPU)
    "deepseek-r1-0528-8b-FLM": {"size_gb": 0, "recipe": "flm"},
    "deepseek-r1-8b-FLM": {"size_gb": 0, "recipe": "flm"},
    "gemma3-1b-FLM": {"size_gb": 0, "recipe": "flm"},
    "gemma3-4b-FLM": {"size_gb": 0, "recipe": "flm"},
    "gpt-oss-20b-FLM": {"size_gb": 0, "recipe": "flm"},
    "gpt-oss-sg-20b-FLM": {"size_gb": 0, "recipe": "flm"},
    "lfm2-1.2b-FLM": {"size_gb": 0, "recipe": "flm"},
    "lfm2-2.6b-FLM": {"size_gb": 0, "recipe": "flm"},
    "lfm2-trans-2.6b-FLM": {"size_gb": 0, "recipe": "flm"},
    "lfm2.5-it-1.2b-FLM": {"size_gb": 0, "recipe": "flm"},
    "lfm2.5-tk-1.2b-FLM": {"size_gb": 0, "recipe": "flm"},
    "llama3.1-8b-FLM": {"size_gb": 0, "recipe": "flm"},
    "llama3.2-1b-FLM": {"size_gb": 0, "recipe": "flm"},
    "llama3.2-3b-FLM": {"size_gb": 0, "recipe": "flm"},
    "medgemma-4b-FLM": {"size_gb": 0, "recipe": "flm"},
    "medgemma1.5-4b-FLM": {"size_gb": 0, "recipe": "flm"},
    "phi4-mini-it-4b-FLM": {"size_gb": 0, "recipe": "flm"},
    "qwen2.5-it-3b-FLM": {"size_gb": 0, "recipe": "flm"},
    "qwen2.5vl-it-3b-FLM": {"size_gb": 0, "recipe": "flm"},
    "qwen3-0.6b-FLM": {"size_gb": 0, "recipe": "flm"},
    "qwen3-1.7b-FLM": {"size_gb": 0, "recipe": "flm"},
    "qwen3-4b-FLM": {"size_gb": 0, "recipe": "flm"},
    "qwen3-8b-FLM": {"size_gb": 0, "recipe": "flm"},
    "qwen3-it-4b-FLM": {"size_gb": 0, "recipe": "flm"},
    "qwen3-tk-4b-FLM": {"size_gb": 0, "recipe": "flm"},
    "qwen3.5-4b-FLM": {"size_gb": 0, "recipe": "flm"},
    "qwen3vl-it-4b-FLM": {"size_gb": 0, "recipe": "flm"},
    "translategemma-4b-FLM": {"size_gb": 0, "recipe": "flm"},
}

TTS_MODELS: dict[str, dict] = {
    "kokoro-v1": {"size_gb": 0.34, "recipe": "kokoro"},
}

# ── Backend mapping ──────────────────────────────────────────────────────────
# Maps the add-on backend string to Lemonade load-request keys.
# Format: "recipe:device" → dict of extra kwargs for POST /api/v1/load
BACKEND_LOAD_KWARGS: dict[str, dict] = {
    # STT
    "whispercpp:cpu": {"whispercpp_backend": "cpu"},
    "whispercpp:npu": {"whispercpp_backend": "npu"},
    "whispercpp:vulkan": {"whispercpp_backend": "vulkan"},
    "flm:npu": {},  # FLM uses its own recipe
    # LLM
    "llamacpp:vulkan": {"llamacpp_backend": "vulkan"},
    "llamacpp:rocm": {"llamacpp_backend": "rocm"},
    "llamacpp:cpu": {"llamacpp_backend": "cpu"},
    "llamacpp:metal": {"llamacpp_backend": "metal"},
    "ryzenai:npu": {},
}

# ── Misc ─────────────────────────────────────────────────────────────────────
LEMONADE_STARTUP_TIMEOUT = 60  # seconds to wait for lemond to become healthy
LEMONADE_HEALTH_POLL_INTERVAL = 2  # seconds between health-check retries
MODEL_PULL_TIMEOUT = 1800  # 30 min max per model download
