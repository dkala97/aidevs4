from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any
from PIL import Image

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

MIME_TO_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}

native_tools = [
    {
        "type": "function",
        "name": "understand_image",
        "description": "Analyze a local image and answer questions about visible content. You can optionally restrict analysis to a rectangular region by passing x, y, width, height in pixels.",
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
                "x": {
                    "type": ["integer", "null"],
                    "description": "Left pixel coordinate of the region (0-based). Pass null when not using region mode.",
                },
                "y": {
                    "type": ["integer", "null"],
                    "description": "Top pixel coordinate of the region (0-based). Pass null when not using region mode.",
                },
                "width": {
                    "type": ["integer", "null"],
                    "description": "Region width in pixels. Pass null when not using region mode.",
                },
                "height": {
                    "type": ["integer", "null"],
                    "description": "Region height in pixels. Pass null when not using region mode.",
                },
            },
            "required": ["image_path", "question", "x", "y", "width", "height"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_image_size",
        "description": "Get local image dimensions in pixels.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to an image file relative to the project root, for example 'dane/scan.png'.",
                }
            },
            "required": ["image_path"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


def is_native_tool(name: str) -> bool:
    return name in {"understand_image", "get_image_size"}


async def execute_native_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "understand_image":
        return await understand_image(**arguments)
    if name == "get_image_size":
        return await get_image_size(**arguments)

    raise RuntimeError(f"Unknown native tool: {name}")


async def understand_image(
    image_path: str,
    question: str,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    full_path = _resolve_project_path(image_path)
    if not full_path.is_file():
        raise RuntimeError(f"Image file not found: {image_path}")

    mime_type = MIME_TYPES.get(full_path.suffix.lower())
    if not mime_type:
        raise RuntimeError(f"Unsupported image format: {full_path.suffix}")

    region = _parse_region(x=x, y=y, width=width, height=height)

    log.vision(image_path, question)

    image_bytes = full_path.read_bytes()
    if region is not None:
        image_bytes, mime_type = _crop_image_bytes(
            image_bytes=image_bytes,
            source_mime_type=mime_type,
            region=region,
        )

    image_base64 = base64.b64encode(image_bytes).decode("ascii")
    answer = analyze_image(
        image_base64=image_base64,
        mime_type=mime_type,
        question=question,
    )

    log.vision_result(answer)
    return {
        "answer": answer,
        "image_path": image_path,
        "region": region,
    }


async def get_image_size(image_path: str) -> dict[str, Any]:
    full_path = _resolve_project_path(image_path)
    if not full_path.is_file():
        raise RuntimeError(f"Image file not found: {image_path}")

    mime_type = MIME_TYPES.get(full_path.suffix.lower())
    if not mime_type:
        raise RuntimeError(f"Unsupported image format: {full_path.suffix}")

    try:
        with Image.open(full_path) as image:
            width, height = image.size
    except Exception as error:
        raise RuntimeError(f"Failed to read image size: {error}") from error

    return {
        "image_path": image_path,
        "width": width,
        "height": height,
        "unit": "px",
    }

def _resolve_project_path(relative_path: str) -> Path:
    candidate = (PROJECT_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise RuntimeError("image_path must stay inside the project root") from error
    return candidate


def _parse_region(
    *,
    x: int | None,
    y: int | None,
    width: int | None,
    height: int | None,
) -> dict[str, int] | None:
    values = (x, y, width, height)
    if all(value is None for value in values):
        return None

    if any(value is None for value in values):
        raise RuntimeError("Region mode requires all of: x, y, width, height")

    assert x is not None and y is not None and width is not None and height is not None

    if x < 0 or y < 0:
        raise RuntimeError("x and y must be >= 0")
    if width <= 0 or height <= 0:
        raise RuntimeError("width and height must be > 0")

    return {"x": x, "y": y, "width": width, "height": height}


def _crop_image_bytes(
    *,
    image_bytes: bytes,
    source_mime_type: str,
    region: dict[str, int],
) -> tuple[bytes, str]:
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.load()
            image_width, image_height = image.size

            x = region["x"]
            y = region["y"]
            width = region["width"]
            height = region["height"]

            if x >= image_width or y >= image_height:
                raise RuntimeError(
                    f"Region origin out of bounds for image size {image_width}x{image_height}"
                )

            right = x + width
            bottom = y + height
            if right > image_width or bottom > image_height:
                raise RuntimeError(
                    "Region extends beyond image bounds: "
                    f"requested x={x}, y={y}, width={width}, height={height}, "
                    f"image={image_width}x{image_height}"
                )

            cropped = image.crop((x, y, right, bottom))

            if source_mime_type == "image/jpeg":
                output_buffer = io.BytesIO()
                if cropped.mode in {"RGBA", "LA", "P"}:
                    cropped = cropped.convert("RGB")
                cropped.save(output_buffer, format="JPEG")
                return output_buffer.getvalue(), "image/jpeg"

            output_buffer = io.BytesIO()
            cropped.save(output_buffer, format="PNG")
            return output_buffer.getvalue(), "image/png"
    except RuntimeError:
        raise
    except Exception as error:
        raise RuntimeError(f"Failed to crop image region: {error}") from error