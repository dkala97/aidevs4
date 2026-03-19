from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.py"
_SPEC = importlib.util.spec_from_file_location("vision_agent_root_config", _ROOT_CONFIG_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load config module from {_ROOT_CONFIG_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

PROJECT_ROOT = _MODULE.PROJECT_ROOT
AI_API_KEY = _MODULE.AI_API_KEY
EXTRA_API_HEADERS = _MODULE.EXTRA_API_HEADERS
REQUEST_TIMEOUT_SECONDS = _MODULE.REQUEST_TIMEOUT_SECONDS
RESPONSES_API_ENDPOINT = _MODULE.RESPONSES_API_ENDPOINT
VISION_MODEL = _MODULE.VISION_MODEL
