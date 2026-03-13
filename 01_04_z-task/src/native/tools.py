from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT
from ..logger import log
from .vision import analyze_image

MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}

native_tools = [
    {
        "type": "function",
        "name": "understand_image",
        "description": "Analyze a local image and answer questions about visible content. Use this for scans, screenshots, tables, text, forms, and other image-based documents.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to an image file relative to the 01_04_z-task project root, for example 'dane/scan.png'.",
                },
                "question": {
                    "type": "string",
                    "description": "Question about the image content.",
                },
            },
            "required": ["image_path", "question"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


def is_native_tool(name: str) -> bool:
    return name == "understand_image"


async def execute_native_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name != "understand_image":
        raise RuntimeError(f"Unknown native tool: {name}")

    return await understand_image(**arguments)


async def understand_image(image_path: str, question: str) -> dict[str, Any]:
    full_path = _resolve_project_path(image_path)
    if not full_path.is_file():
        raise RuntimeError(f"Image file not found: {image_path}")

    mime_type = MIME_TYPES.get(full_path.suffix.lower())
    if not mime_type:
        raise RuntimeError(f"Unsupported image format: {full_path.suffix}")

    log.vision(image_path, question)

    image_bytes = full_path.read_bytes()
    image_base64 = base64.b64encode(image_bytes).decode("ascii")
    answer = analyze_image(
        image_base64=image_base64,
        mime_type=mime_type,
        question=question,
    )

    log.vision_result(answer)
    return {"answer": answer, "image_path": image_path}


def _resolve_project_path(relative_path: str) -> Path:
    candidate = (PROJECT_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise RuntimeError("image_path must stay inside the project root") from error
    return candidate