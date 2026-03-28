from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent
ENV_PATH = REPO_ROOT / ".env"

# Load environment variables
load_dotenv(ENV_PATH)

# API Configuration
HUB_URL = os.getenv("HUB_URL", "")
HUB_API_KEY = os.getenv("HUB_API_KEY", "")

# Task Configuration
TASK_NAME = "firmware"

# Agent Instructions
INSTRUCTIONS = """
You are a precise, tool-driven agent.
"""
