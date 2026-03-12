from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(ENV_PATH)

AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

if AI_PROVIDER == "openrouter":
    AI_API_KEY = OPENROUTER_API_KEY
    AI_BASE_URL = "https://openrouter.ai/api/v1"
    MODEL = os.getenv("MODEL", "anthropic/claude-haiku-4.5").strip()
else:
    AI_API_KEY = OPENAI_API_KEY
    AI_BASE_URL = None
    MODEL = os.getenv("MODEL", "gpt-5-mini").strip()

if not AI_API_KEY:
    raise RuntimeError(f"Brak klucza API dla providera '{AI_PROVIDER}'. Uzupełnij .env")

client_kwargs: dict[str, str] = {"api_key": AI_API_KEY}
if AI_BASE_URL:
    client_kwargs["base_url"] = AI_BASE_URL

ai = OpenAI(**client_kwargs)

SERVER_HOST = os.getenv("PROXY_HOST", "0.0.0.0").strip()
SERVER_PORT = int(os.getenv("PROXY_PORT", "8443"))

MAX_TOOL_ROUNDS = int(os.getenv("MAX_TOOL_ROUNDS", "5"))
MAX_HISTORY_ITEMS = int(os.getenv("MAX_HISTORY_ITEMS", "80"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))

PARCELS_MCP_URL = os.getenv("PARCELS_MCP_URL", "").strip()
PARCELS_MCP_HOST = os.getenv("PARCELS_MCP_HOST", "127.0.0.1").strip()
PARCELS_MCP_PORT = int(os.getenv("PARCELS_MCP_PORT", "3000"))
