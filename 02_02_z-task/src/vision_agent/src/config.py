from __future__ import annotations

import os

from .shared_config import (
    AI_API_KEY,
    MODEL,
    MAX_OUTPUT_TOKENS,
    EXTRA_API_HEADERS,
    PROJECT_ROOT,
    REQUEST_TIMEOUT_SECONDS,
    RESPONSES_API_ENDPOINT,
    VISION_MODEL,
    AI_PROVIDER
)

INSTRUCTIONS = os.getenv(
    "VISION_AGENT_INSTRUCTIONS",
    """
You are a precise vision worker.

Use tools when needed:
- understand_image: inspect image content and answer questions.
- modify_image: apply visual edits to an existing local image.

Rules:
- Always use exact workspace-relative image paths.
- If user provides region coordinates, call understand_image with x, y, width, height.
- Keep operations inside the project root.
- Return concise, factual results.
""".strip(),
)
