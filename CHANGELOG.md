# Changelog

## 0.3.13

- Fix: completely rewrite `config_flow.py` which was corrupted by a prior
  string-replacement operation, causing duplicate class definitions and loose
  code outside classes. The corrupted file prevented the module from importing,
  producing the "Invalid handler specified" error when clicking the integration.

## 0.3.12

- Fix: replace `ConfigFlowResult` (added HA 2024.4) with `FlowResult` from
  `homeassistant.data_entry_flow` which is available in all HA versions.
  `ConfigFlowResult` import caused an `ImportError` when the user clicked the
  integration, producing the "Invalid handler specified" error.

## 0.3.11

- Fix: add `config:rw` to map alongside `homeassistant:rw` so the HA config dir
  is accessible at both `/homeassistant` and `/config` regardless of supervisor version
- Fix: run script now detects HA config dir by presence of `configuration.yaml`
  (reliable) rather than just checking if the directory exists
- Added diagnostic log lines showing which paths exist and whether they contain
  `configuration.yaml`, so the next log will show exactly where files are landing

## 0.3.10

- Fix: replace `httpx` with `aiohttp` (always bundled with HA) — no external pip requirements.
  If HA failed to install `httpx` from PyPI (network issue, pip failure, etc.), the integration
  would silently not load. With zero requirements, nothing can block loading.
- Remove `requirements` from manifest entirely (empty list)

## 0.3.9

- Fix: add `"dependencies": ["conversation"]` and `"after_dependencies": ["assist_pipeline", "intent"]`
  to manifest — without declaring the conversation dependency, HA silently skips loading
  the integration so it never appears in the UI
- Restore `"integration_type": "service"` (correct value per working reference integrations)

## 0.3.8

- Fix: lazy-import `LemonadeClient` (and `httpx`) inside `async_step_user` instead of at
  module load time — HA attempts to import `config_flow.py` before installing requirements,
  so a top-level `import httpx` raised a silent `ImportError` preventing the integration
  from ever appearing in the Add Integration dialog
- Remove auto-restart from add-on run script (unreliable); run script now logs the exact
  destination path and a clear manual restart reminder

## 0.3.7

- Fix: remove invalid `quality_scale: "custom"` from manifest (not a valid HA enum value,
  caused manifest validation failure so integration never appeared in the UI)
- Fix: change `integration_type` from `"service"` to `"hub"` (correct type for a local integration)
- Fix: run script now calls `ha core restart` automatically after installing the component,
  eliminating the timing race where HA finishes scanning before the add-on finishes copying

## 0.3.6

- Fix: add `custom_components/lemonade_ha/translations/en.json` so HA can
  discover the integration in the "Add Integration" dialog
  (HA reads `translations/en.json` at runtime; `strings.json` alone is not enough)

## 0.3.5

- Fix: add `s6-rc.d/user/contents.d/lemonade-ha` so s6-overlay actually starts the service
  (without this file the run script was silently skipped and nothing happened)

## 0.3.4

- Remove HEALTHCHECK — Docker now marks container healthy immediately,
  stopping the HA watchdog restart loop
- Add build-time import verification to catch Python errors during `docker build`

## 0.3.3

- Add native HA custom integration (`custom_components/lemonade_wyoming`)
  which registers STT, TTS, and conversation agent directly — no manual
  Wyoming Protocol integration entries needed
- Add-on automatically copies the custom component to the HA config directory
  on startup; restart HA once to load it, then configure via
  Settings → Devices & Services → Add Integration → Lemonade HA

## 0.3.2

- Fix HEALTHCHECK: use `nc -z` (port-open check) instead of Wyoming protocol
  framing that was always failing and causing the watchdog restart loop

## 0.3.1

- Fix HEALTHCHECK start-period from 10 minutes to 30 seconds so HA Supervisor
  sees the container as healthy within its 120-second startup window

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
