# Changelog

## 0.3.0

- Fix startup timeout: Wyoming TCP ports now open immediately; Lemonade
  connection and model downloads happen in the background
- Handlers queue voice requests until Lemonade is ready (up to 10 minutes)
  instead of failing with a timeout error

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
