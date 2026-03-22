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
TASK_NAME = "failure"
MAX_TOKENS_LIMIT = 1500
COMPRESS_BATCH_SIZE = int(os.getenv("FAILURE_COMPRESS_BATCH_SIZE", "10"))
COMPRESS_MODEL = os.getenv("FAILURE_COMPRESS_MODEL", "gpt-5.2")
COMPRESS_MAX_OUTPUT_TOKENS = int(os.getenv("FAILURE_COMPRESS_MAX_OUTPUT_TOKENS", "512"))

# Agent Instructions
INSTRUCTIONS = """
You are a precise, tool-driven agent. Follow these general principles when working with files:

WORKING WITH LARGE FILES — never load full file content into context:
- Sample first: use fs_read with a line range (e.g. lines 1-50, then mid-file, then end) to
  understand structure and content patterns before acting on the whole file.
- Search, don't read: use fs_search with patternMode="regex" or "literal" to locate specific
  line numbers — then act only on those lines.
- Edit in place: use fs_write with action="delete_lines" or "replace" targeting specific line
  ranges rather than rewriting entire files.
- Work on copies: use fs_manage (copy) to create a working copy before making destructive edits,
  so the original is always preserved for recovery.
- Verify without reading: use count_tokens on a file path to check size constraints without
  pulling content into context.

GENERAL RULES:
- Use dryRun=true on fs_write to preview changes before applying.
- Prefer many small targeted edits over loading and rewriting large files.
"""
