from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import requests

from .config import AgentConfig
from .logger import log

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

class ToolVisionConfig:
    def __init__(self, vision_model: str):
        self.VISION_MODEL = vision_model

def create_tool_schema_vision(tool_name: str = "vision"):
    return {
        "type": "function",
        "name": tool_name,
        "description": "Analyze a local image and answer questions about visible content..",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to an image file relative to the workspace root, for example 'data/scan.png'.",
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

class ToolVision:
    def __init__(self, shared_config: AgentConfig, vision_config: ToolVisionConfig) -> None:
        self._next_allowed_epoch = 0.0
        self._shared_config = shared_config
        self._vision_config = vision_config

    async def call(self, params: dict[str, Any]) ->Any:
        try:
            return await self._call_throwing(params)
        except Exception as ex:
            return { "status": f"error: {ex}" }

    async def _call_throwing(self, params: dict[str, Any]) -> Any:
        if not isinstance(params, dict):
            raise RuntimeError("Invalid parameters type")

        if not "image_path" in params:
            raise RuntimeError("Missing image_path in provided parameters")

        if not "question" in params:
            raise RuntimeError("Missing question in provided parameters")

        image_path = params["image_path"]
        question = params["question"]

        full_path = self._resolve_workspace_path(image_path)
        if not full_path.is_file():
            raise RuntimeError(f"Image file not found: {image_path}")

        mime_type = MIME_TYPES.get(full_path.suffix.lower())
        if not mime_type:
            raise RuntimeError(f"Unsupported image format: {full_path.suffix}")

        log.vision(image_path, question)

        image_bytes = full_path.read_bytes()
        image_base64 = base64.b64encode(image_bytes).decode("ascii")
        answer = self._analyze_image(
            image_base64=image_base64,
            mime_type=mime_type,
            question=question,
        )

        log.vision_result(answer)
        return {"answer": answer, "image_path": image_path}

    def _analyze_image(self, image_base64: str, mime_type: str, question: str) -> str:
        response = requests.post(
            self._shared_config.RESPONSES_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._shared_config.AI_API_KEY}",
                **self._shared_config.EXTRA_API_HEADERS,
            },
            json={
                "model": self._vision_config.VISION_MODEL,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": question},
                            {
                                "type": "input_image",
                                "image_url": f"data:{mime_type};base64,{image_base64}",
                            },
                        ],
                    }
                ],
            },
            timeout=self._shared_config.REQUEST_TIMEOUT_SECONDS,
        )

        data: dict[str, Any] = response.json()
        if not response.ok or data.get("error"):
            message = data.get("error", {}).get("message") or f"Vision request failed ({response.status_code})"
            raise RuntimeError(message)

        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text", "").strip():
                    return content["text"].strip()

        return "No response"


    def _resolve_workspace_path(self, relative_path: str) -> Path:
        candidate = (self._shared_config.PROJECT_ROOT / "workspace" / relative_path).resolve()
        try:
            candidate.relative_to(self._shared_config.PROJECT_ROOT / "workspace")
        except ValueError as error:
            raise RuntimeError("image_path must stay inside the project root") from error
        return candidate
