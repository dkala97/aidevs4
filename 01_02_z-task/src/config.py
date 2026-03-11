from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

TASK_NAME = "findhim"
MAX_TOOL_ROUNDS = 15

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
ENV_PATH = ROOT_DIR / ".env"
WORKERS_PATH = BASE_DIR / "transport_workers.json"

load_dotenv(ENV_PATH)

AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
HUB_URL = os.getenv("HUB_URL", "").strip().rstrip("/")
HUB_API_KEY = os.getenv("HUB_API_KEY", "").strip()

if AI_PROVIDER == "openrouter":
    API_KEY = OPENROUTER_API_KEY
    BASE_URL = "https://openrouter.ai/api/v1"
    MODEL = "openai/gpt-5-mini"
else:
    API_KEY = OPENAI_API_KEY
    BASE_URL = None
    MODEL = "gpt-5-mini"

if not API_KEY:
    print(f"Błąd: brak klucza API dla providera '{AI_PROVIDER}'", file=sys.stderr)
    sys.exit(1)

if not HUB_API_KEY:
    print("Błąd: brak HUB_API_KEY w .env", file=sys.stderr)
    sys.exit(1)

client_kwargs = {"api_key": API_KEY}
if BASE_URL:
    client_kwargs["base_url"] = BASE_URL

ai = OpenAI(**client_kwargs)
