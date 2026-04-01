# Changelog

## 0.2.0

- Restructure LLM configuration by backend (llamacpp / ryzenai / flm)
- Full model list from server_models.json (~110 models across all backends)
- Per-backend model dropdowns in HA configuration UI

## 0.1.0

- Initial release
- Speech-to-Text via Whisper (whisper.cpp / FastFlowLM)
- LLM conversation agent via LLama.cpp / RyzenAI / FastFlowLM
- Text-to-Speech via Kokoro
- Automatic model download on first launch
- Home Assistant add-on with configuration UI
