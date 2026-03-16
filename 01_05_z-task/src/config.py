from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent
ENV_PATH = REPO_ROOT / ".env"

load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
REQUESTED_PROVIDER = os.getenv("AI_PROVIDER", "").strip().lower()

RESPONSES_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/responses",
    "openrouter": "https://openrouter.ai/api/v1/responses",
}

VALID_PROVIDERS = {"openai", "openrouter"}
OPENROUTER_ONLINE_SUFFIX = ":online"


def _resolve_provider() -> str:
    if REQUESTED_PROVIDER and REQUESTED_PROVIDER not in VALID_PROVIDERS:
        raise RuntimeError("AI_PROVIDER must be one of: openai, openrouter")

    if REQUESTED_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise RuntimeError("AI_PROVIDER=openai requires OPENAI_API_KEY")
        return REQUESTED_PROVIDER

    if REQUESTED_PROVIDER == "openrouter":
        if not OPENROUTER_API_KEY:
            raise RuntimeError("AI_PROVIDER=openrouter requires OPENROUTER_API_KEY")
        return REQUESTED_PROVIDER

    if OPENAI_API_KEY:
        return "openai"

    if OPENROUTER_API_KEY:
        return "openrouter"

    raise RuntimeError("Missing AI API key. Set OPENAI_API_KEY or OPENROUTER_API_KEY in the repo root .env file.")


AI_PROVIDER = _resolve_provider()
AI_API_KEY = OPENAI_API_KEY if AI_PROVIDER == "openai" else OPENROUTER_API_KEY
RESPONSES_API_ENDPOINT = RESPONSES_ENDPOINTS[AI_PROVIDER]

EXTRA_API_HEADERS: dict[str, str] = {}
if AI_PROVIDER == "openrouter":
    http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
    app_name = os.getenv("OPENROUTER_APP_NAME", "").strip()
    if http_referer:
        EXTRA_API_HEADERS["HTTP-Referer"] = http_referer
    if app_name:
        EXTRA_API_HEADERS["X-Title"] = app_name


def resolve_model_for_provider(model: str) -> str:
    model = model.strip()
    if not model:
        raise RuntimeError("Model must be a non-empty string")

    if AI_PROVIDER != "openrouter" or "/" in model:
        return model

    if model.endswith(OPENROUTER_ONLINE_SUFFIX):
        return model

    return f"openai/{model}" if model.startswith("gpt-") else model


MODEL = resolve_model_for_provider(os.getenv("TASK_MODEL", "gpt-5.2"))
MAX_OUTPUT_TOKENS = int(os.getenv("TASK_MAX_OUTPUT_TOKENS", "16384"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("TASK_REQUEST_TIMEOUT", "300"))

AUTO_API_URL = os.getenv("AUTO_API_URL", "").strip()
if not AUTO_API_URL:
    hub_url = os.getenv("HUB_URL", "").strip().rstrip("/")
    if hub_url:
        AUTO_API_URL = f"{hub_url}/verify"

AUTO_API_KEY = os.getenv("AUTO_API_KEY", "").strip() or os.getenv("HUB_API_KEY", "").strip()
AUTO_API_TASK = os.getenv("AUTO_API_TASK", "railway").strip() or "railway"

if not AUTO_API_URL:
    raise RuntimeError("Missing AUTO_API_URL (or HUB_URL) in .env")

if not AUTO_API_KEY:
    raise RuntimeError("Missing AUTO_API_KEY (or HUB_API_KEY) in .env")

MAX_STEPS = int(os.getenv("TASK_MAX_STEPS", "100"))
AUTO_API_503_RETRIES = int(os.getenv("AUTO_API_503_RETRIES", "10"))
AUTO_API_503_SLEEP_SECONDS = float(os.getenv("AUTO_API_503_SLEEP_SECONDS", "10"))

INSTRUCTIONS = """You are an autonomous task agent.

You have 2 native tools:
- auto_api(params) -> calls task API with provided action type and parameters required for requested action.
- sleep(seconds) -> pauses execution.

Rules:
1. Start with auto_api({"action":"help"}) to discover available actions.
2. For every next action, pass that action properties in `params` object passed to auto_api. E.g. auto_api({"action": "someaction", "argument1": "argvalue"}).
3. If auto_api returns wait instruction, call sleep with the exact number of seconds from hint/wait_seconds, then retry the exact same action.
4. Do not invent missing fields; follow API errors and help output exactly.
5. Continue until task is solved and return concise final answer.
""".strip()
