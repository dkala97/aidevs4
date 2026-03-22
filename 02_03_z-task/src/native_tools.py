"""
Native tools for failure log analysis task.
Handles API communication, token counting, and log compression logic.
Files-mcp tools (fs_read, fs_write, fs_search) handle file operations.
"""

import re
from pathlib import Path
from typing import Any

import httpx
import tiktoken

from generic_agent.config import AgentConfig

from .config import (
    PROJECT_ROOT,
    HUB_API_KEY,
    HUB_URL,
    TASK_NAME,
    MAX_TOKENS_LIMIT,
    COMPRESS_BATCH_SIZE,
    COMPRESS_MODEL,
    COMPRESS_MAX_OUTPUT_TOKENS,
)


class FailureLogAnalyzer:
    """Analyzer for power plant failure logs - API and token operations."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self.data_dir = PROJECT_ROOT / "data"
        self.data_dir.mkdir(exist_ok=True)


    def _resolve(self, path_str: str) -> Path:
        """Resolve a path relative to PROJECT_ROOT if not absolute."""
        p = Path(path_str)
        if p.is_absolute():
            return p
        return PROJECT_ROOT / p

    def count_tokens_file(self, file_path: str) -> dict:
        """Count tokens in a file without loading content into model context."""
        try:
            path = self._resolve(file_path)
            text = path.read_text(encoding="utf-8")
            count = self._count_tokens(text)
            return {
                "success": True,
                "file": path.relative_to(PROJECT_ROOT).as_posix(),
                "tokens": count,
                "within_limit": count <= MAX_TOKENS_LIMIT,
            }
        except Exception as e:
            return {"error": str(e)}

    def _count_tokens(self, text: str):
        return len(self.encoding.encode(text))

    def _fallback_shorten_line(self, line: str) -> str:
        match = re.match(r"^(\[[^\]]+\]\s\[[^\]]+\]\s\S+\s+)(.*)$", line.strip())
        if not match:
            return line.strip()[:120]

        prefix, description = match.groups()
        shortened = description if len(description) <= 80 else f"{description[:77].rstrip()}..."
        return f"{prefix}{shortened}"

    async def _compress_batch(self, client: httpx.AsyncClient, batch_lines: list[str]) -> list[str]:
        prompt = (
            "Rewrite each input log line into a shorter single-line version.\n"
            "Rules:\n"
            "- Keep exactly one output line per input line, in the same order.\n"
            "- Make description as short as possible, use key words, no grammarly correct sentences are needed.\n"
            "- Output plain text only, no numbering, no code block.\n"
            "Source format:\n"
            "[YYYY-MM-DD HH:MM] [LEVEL] COMPONENT <description>"
            "Target format:\n"
            "[YYYY-MM-DD HH:MM] [LEVEL] COMPONENT <shorten description>"
        )

        body: dict[str, Any] = {
            "model": COMPRESS_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\n"
                        "Input lines:\n"
                        + "\n".join(batch_lines)
                    ),
                }
            ],
            "max_output_tokens": COMPRESS_MAX_OUTPUT_TOKENS,
        }

        response = await client.post(
            self.config.RESPONSES_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.AI_API_KEY}",
                **self.config.EXTRA_API_HEADERS,
            },
            json=body,
            timeout=self.config.REQUEST_TIMEOUT_SECONDS,
        )
        data = response.json()
        if not response.is_success or data.get("error"):
            message = data.get("error", {}).get("message") or f"Compression request failed ({response.status_code})"
            raise RuntimeError(message)

        outputs = data.get("output", [])
        for output in outputs:
            if output.get("type") != "message":
                continue
            for content in output.get("content", []):
                if content.get("type") == "output_text" and content.get("text", "").strip():
                    output_text = content["text"].strip()
                    break
            if output_text:
                break

        output_lines = [line.strip() for line in output_text.splitlines() if line.strip()]
        if len(output_lines) != len(batch_lines):
            raise RuntimeError(
                f"Compression batch returned {len(output_lines)} lines for {len(batch_lines)} inputs"
            )
        return output_lines

    async def download_logs(self) -> dict:
        url = f"{HUB_URL}/data/{HUB_API_KEY}/failure.log"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                logs_content_raw = response.text
                logs_content = self._preserve_unique_entries_last_timestamp(logs_content_raw)

                # Save to data directory (for fs_read to access)
                output_file = self.data_dir / "failure_log.txt"
                with open(output_file, 'w') as f:
                    f.write(logs_content)

                lines_raw = logs_content_raw.strip().split('\n')
                lines = logs_content.strip().split('\n')
                tokens = self._count_tokens(logs_content)

                return {
                    "success": True,
                    "lines": len(lines),
                    "tokens": tokens,
                    "file": output_file.relative_to(PROJECT_ROOT).as_posix(),
                    "message": f"Downloaded {len(lines_raw)} raw log, extracted {len(lines)} unique lines ({tokens} tokens)"
                }
        except Exception as e:
            return {"error": f"Download failed: {str(e)}"}

    def _preserve_unique_entries_last_timestamp(self, logs: str) -> str:
        log_lines = logs.split("\n")
        seen = []
        unique_logs = []
        for line in reversed(log_lines):
            line_no_timestamp = re.sub("^\\[[0-9-: T.]+\\] ", "", line)
            if line_no_timestamp not in seen:
                seen.append(line_no_timestamp)
                unique_logs.append(line)
        return "\n".join(reversed(unique_logs))


    def filter_lines(self, input_path: str, output_path: str, pattern: str) -> dict:
        try:
            src = self._resolve(input_path)
            dst = self._resolve(output_path)

            raw_lines = src.read_text(encoding="utf-8").splitlines()
            filtered_lines = []

            for line in raw_lines:
                if re.match(pattern, line):
                    filtered_lines.append(line)

            filtered = "\n".join(filtered_lines)
            dst.write_text(filtered + "\n", encoding="utf-8")
            token_count = self._count_tokens(filtered)

            return {
                "success": True,
                "input_file": src.relative_to(PROJECT_ROOT).as_posix(),
                "output_file": dst.relative_to(PROJECT_ROOT).as_posix(),
                "lines": len(filtered_lines),
                "tokens": token_count,
                "message": f"Number of input lines: {len(raw_lines)}, after filtering: {len(filtered_lines)}, {token_count} tokens",
            }

        except Exception as e:
            return {"error": f"Filtering failed: {str(e)}"}

    async def compress_logs(self, input_path: str, output_path: str, max_tokens: int = MAX_TOKENS_LIMIT) -> dict:
        """
        Read a filtered log file, shorten descriptions to fit within the token limit,
        and write the result to output_path. Never loads content into the model context.

        Args:
            input_path: Path to the filtered log file (relative to data_dir or absolute).
            output_path: Path to write compressed output (relative to data_dir or absolute).
            max_tokens: Hard token cap (default 1500).
        """
        try:
            src = self._resolve(input_path)
            dst = self._resolve(output_path)

            log_text = src.read_text(encoding="utf-8")
            raw_lines = log_text.splitlines()
            input_token_count = self._count_tokens(log_text)
            if input_token_count < max_tokens:
                dst.write_text(log_text, encoding="utf-8")
                return {
                    "success": True,
                    "input_file": src.relative_to(PROJECT_ROOT).as_posix(),
                    "output_file": dst.relative_to(PROJECT_ROOT).as_posix(),
                    "lines": len(raw_lines),
                    "tokens": input_token_count,
                    "within_limit": input_token_count <= max_tokens,
                    "batch_size": COMPRESS_BATCH_SIZE,
                    "model": COMPRESS_MODEL,
                    "message": f"Text within tokens limit, copied unchanged content to output file",
                }

            compressed = []

            filtered_lines = [line.strip() for line in raw_lines if line.strip()]

            async with httpx.AsyncClient() as client:
                for index in range(0, len(filtered_lines), COMPRESS_BATCH_SIZE):
                    batch = filtered_lines[index : index + COMPRESS_BATCH_SIZE]
                    # try:
                    compressed.extend(await self._compress_batch(client, batch))
                    # except Exception:
                        # compressed.extend(self._fallback_shorten_line(line) for line in batch)

            final_text = '\n'.join(compressed)
            token_count = self._count_tokens(final_text)

            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(final_text + '\n', encoding="utf-8")

            return {
                "success": True,
                "input_file": src.relative_to(PROJECT_ROOT).as_posix(),
                "output_file": dst.relative_to(PROJECT_ROOT).as_posix(),
                "lines": len(compressed),
                "tokens": token_count,
                "within_limit": token_count <= max_tokens,
                "batch_size": COMPRESS_BATCH_SIZE,
                "model": COMPRESS_MODEL,
                "message": f"Compressed {len(compressed)} lines in batches of {COMPRESS_BATCH_SIZE} -> {token_count} tokens",
            }

        except Exception as e:
            return {"error": f"Compression failed: {str(e)}"}

    async def submit_to_centrala(self, logs_path: str) -> dict:
        """Read compressed logs from a file and submit to Centrala."""
        try:
            path = self._resolve(logs_path)
            logs = path.read_text(encoding="utf-8").strip()
        except Exception as e:
            return {"error": f"Could not read logs file '{logs_path}': {e}"}

        if not logs:
            return {"error": "Logs file is empty"}

        payload = {
            "apikey": HUB_API_KEY,
            "task": TASK_NAME,
            "answer": {
                "logs": logs
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{HUB_URL}/verify", json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"error": f"Submission failed: {e.response.text if e.response.text else str(e)}"}

