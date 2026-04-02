"""Lemonade HA — constants."""

DOMAIN = "lemonade_ha"

# Config entry keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_STT_MODEL = "stt_model"
CONF_STT_LANGUAGE = "stt_language"
CONF_LLM_MODEL = "llm_model"
CONF_LLM_SYSTEM_PROMPT = "llm_system_prompt"
CONF_LLM_MAX_TOKENS = "llm_max_tokens"
CONF_TTS_MODEL = "tts_model"
CONF_TTS_VOICE = "tts_voice"

# Defaults
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000
DEFAULT_STT_MODEL = "Whisper-Large-v3-Turbo"
DEFAULT_STT_LANGUAGE = "en"
DEFAULT_LLM_MODEL = "Qwen3-4B-GGUF"
DEFAULT_LLM_MAX_TOKENS = 1024
DEFAULT_TTS_MODEL = "kokoro-v1"
DEFAULT_TTS_VOICE = "af_heart"
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful smart-home voice assistant called Lemonade. "
    "Answer concisely in one or two sentences unless asked for more detail."
)

# Lemonade HTTP API
API_PREFIX = "/api/v1"
EP_HEALTH = f"{API_PREFIX}/health"
EP_TRANSCRIPTIONS = f"{API_PREFIX}/audio/transcriptions"
EP_CHAT_COMPLETIONS = f"{API_PREFIX}/chat/completions"
EP_SPEECH = f"{API_PREFIX}/audio/speech"

# Audio — Whisper expects 16 kHz / 16-bit / mono
WHISPER_SAMPLE_RATE = 16000
WHISPER_SAMPLE_WIDTH = 2
WHISPER_CHANNELS = 1

# Audio — Kokoro outputs 24 kHz / 16-bit / mono
KOKORO_SAMPLE_RATE = 24000
KOKORO_SAMPLE_WIDTH = 2
KOKORO_CHANNELS = 1

PLATFORMS = ["stt", "tts", "conversation"]
