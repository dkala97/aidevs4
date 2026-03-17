from __future__ import annotations

from datetime import datetime


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


class _Logger:
    def info(self, message: str) -> None:
        print(f"[{_timestamp()}] {message}")

    def success(self, message: str) -> None:
        print(f"[{_timestamp()}] OK  {message}")

    def warn(self, message: str) -> None:
        print(f"[{_timestamp()}] WARN {message}")

    def error(self, title: str, message: str | None = None) -> None:
        suffix = f": {message}" if message else ""
        print(f"[{_timestamp()}] ERR {title}{suffix}")

    def start(self, message: str) -> None:
        print(f"[{_timestamp()}] -> {message}")

    def box(self, text: str) -> None:
        lines = text.splitlines() or [text]
        width = max(len(line) for line in lines)
        border = "=" * (width + 4)
        print()
        print(border)
        for line in lines:
            print(f"| {line.ljust(width)} |")
        print(border)
        print()

    def query(self, query: str) -> None:
        print(f"\nQUERY: {query}\n")

    def api(self, step: int, message_count: int) -> None:
        print(f"[{_timestamp()}] API step {step} ({message_count} messages)")

    def api_done(self, usage: dict | None) -> None:
        if not usage:
            return
        input_tokens = usage.get("input_tokens", "?")
        output_tokens = usage.get("output_tokens", "?")
        print(f"[{_timestamp()}] tokens: {input_tokens} in / {output_tokens} out")

    def tool(self, name: str, arguments: dict) -> None:
        print(f"[{_timestamp()}] TOOL {name}")
        if arguments:
            print(f"       args: {arguments}")

    def tool_result(self, name: str, success: bool, output: str) -> None:
        status = "OK" if success else "ERR"
        print(f"[{_timestamp()}] TOOL {name} -> {status}")
        if output:
            lines = output.split("\n")
            for line in lines[:3]:  # Show first 3 lines
                print(f"       {line}")
            if len(lines) > 3:
                print(f"       ... ({len(lines) - 3} more lines)")

    def http_request(self, method: str, url: str, payload: dict | None = None) -> None:
        print(f"[{_timestamp()}] HTTP {method} {url}")
        if payload:
            print(f"       payload: {payload}")

    def http_response(self, status_code: int, success: bool, response_data: dict | str | None = None) -> None:
        status = "OK" if success else "ERR"
        print(f"[{_timestamp()}] HTTP -> {status} ({status_code})")
        if response_data:
            if isinstance(response_data, dict):
                import json
                data_str = json.dumps(response_data)
            else:
                data_str = str(response_data)
            lines = data_str.split("\n")
            for line in lines[:2]:  # Show first 2 lines
                print(f"       {line}")
            if len(lines) > 2:
                print(f"       ... ({len(lines) - 2} more lines)")


log = _Logger()
