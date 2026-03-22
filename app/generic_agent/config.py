from __future__ import annotations

import os

from dotenv import load_dotenv
from pathlib import Path

class AgentConfig:
    def __init__(self, dotenv_path: str, project_root: Path, instructions: str):
        load_dotenv(dotenv_path)

        self.PROJECT_ROOT=Path(project_root)
        self.INSTRUCTIONS=instructions

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
        self.AI_API_KEY = OPENAI_API_KEY if AI_PROVIDER == "openai" else OPENROUTER_API_KEY
        self.RESPONSES_API_ENDPOINT = RESPONSES_ENDPOINTS[AI_PROVIDER]

        self.EXTRA_API_HEADERS: dict[str, str] = {}
        if AI_PROVIDER == "openrouter":
            http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
            app_name = os.getenv("OPENROUTER_APP_NAME", "").strip()
            if http_referer:
                self.EXTRA_API_HEADERS["HTTP-Referer"] = http_referer
            if app_name:
                self.EXTRA_API_HEADERS["X-Title"] = app_name


        def resolve_model_for_provider(model: str) -> str:
            model = model.strip()
            if not model:
                raise RuntimeError("Model must be a non-empty string")

            if AI_PROVIDER != "openrouter" or "/" in model:
                return model

            if model.endswith(OPENROUTER_ONLINE_SUFFIX):
                return model

            return f"openai/{model}" if model.startswith("gpt-") else model


        self.MODEL = resolve_model_for_provider(os.getenv("TASK_MODEL", "gpt-5.2"))
        self.MAX_OUTPUT_TOKENS = int(os.getenv("TASK_MAX_OUTPUT_TOKENS", "16384"))
        self.REQUEST_TIMEOUT_SECONDS = int(os.getenv("TASK_REQUEST_TIMEOUT", "300"))
        self.MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "100"))
