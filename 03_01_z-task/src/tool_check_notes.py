from __future__ import annotations

import asyncio
import json
from typing import Any

from generic_agent.config import AgentConfig
from generic_agent.logger import log
from generic_agent.utils import resolve_workspace_path
from generic_agent.api import chat, extract_text

def create_tool_schema_check_notes(tool_name: str = "check_notes"):
    return {
        "type": "function",
        "name": tool_name,
        "description": "Check notes from sensor JSON files, classify them using LLM, and filter sensors matching the target class. Reads JSON files from input directory, extracts operator_notes field, classifies notes in batches, and writes matching sensor IDs to result file.",
        "parameters": {
            "type": "object",
            "properties": {
                "input_dir": {
                    "type": "string",
                    "description": "Directory path containing sensor JSON files with operator_notes field.",
                },
                "result_filepath": {
                    "type": "string",
                    "description": "Output file path where filtered sensor IDs will be written (one per line).",
                },
                "batch_size": {
                    "type": "integer",
                    "description": "Number of unique notes to classify per LLM batch request.",
                },
                "classification_rules": {
                    "type": "string",
                    "description": "Rules for classifying notes (e.g., criteria for correct vs failed readings).",
                },
                "target_class": {
                    "type": "string",
                    "description": "The classification class to filter for (e.g., 'failed' or 'correct').",
                },
            },
            "required": ["input_dir", "result_filepath", "batch_size", "classification_rules", "target_class"],
            "additionalProperties": False,
        },
        "strict": True,
    }

class ToolCheckNotes:
    def __init__(self, shared_config: AgentConfig):
        self._shared_config = shared_config

    async def call(self, params: dict[str, Any]) ->Any:
        if "input_dir" not in params or "result_filepath" not in params or "batch_size" not in params or "classification_rules" not in params or "target_class" not in params:
            return { "status": "error: Missing some of required parameters: input_dir or result_filepath or batch_size or classification_rules or target_class" }
        input_dir = params["input_dir"]
        result_filepath = params["result_filepath"]
        batch_size = params["batch_size"]
        classification_rules = params["classification_rules"]
        target_class = params["target_class"]

        input_fullpath = resolve_workspace_path(self._shared_config, input_dir)
        result_fullpath = resolve_workspace_path(self._shared_config, result_filepath)

        if not input_fullpath.exists():
            return { "status": f"error: File doesn't exists {input_fullpath}" }

        result_fullpath.parent.mkdir(parents=True, exist_ok=True)

        notes_map: dict[str, list[str]] = {}

        for sensor_filepath in input_fullpath.glob("*.json"):
            with sensor_filepath.open() as sensor_file:
                sensor_data = json.load(sensor_file)
                try:
                    if "operator_notes" not in sensor_data:
                        raise RuntimeError("Missing operator_notes")
                    if not sensor_data["operator_notes"] in notes_map:
                        notes_map[sensor_data["operator_notes"]] = []
                    notes_map[sensor_data["operator_notes"]].append(sensor_filepath.stem)
                except Exception as ex:
                    sensor_id = sensor_filepath.stem
                    return {
                        "status": f"Validation failed for {sensor_id} with: {ex}",
                        "sensor_id": sensor_id
                    }

        notes_unique = notes_map.keys()
        filtered = []

        for i in range(0, len(notes_unique), batch_size):
            batch = list(notes_unique)[i:i + batch_size]
            try:
                classification = self._classify_batch(batch, classification_rules)
                for note, assigned_class in zip(batch, classification):
                    if assigned_class == target_class:
                        filtered.extend(notes_map[note])
            except Exception as ex:
                sensor_id = sensor_filepath.stem
                return {
                    "status": f"Notes clarification failed with: {ex}"
                }

        with result_fullpath.open("w") as result_file:
            result_file.write("\n".join(filtered))

        # await asyncio.sleep(0.001)

        status = f"Ranges check done, number of failed sensors: {len(filtered)}"
        log.info(status)
        return {
            "status": status,
            "failed_sensors": len(filtered),
            "result_filepath": result_filepath
        }

    def _classify_batch(self, notes_batch: list[str], classification_rules: str):
        instruction=f"""
Your are responsible for classification of the following notes batch.
List of notes is the json list of strings. Classify each note and assign it best matching class. In output provide only list of assigned classes. Each class shall be at the as position as note is in the input array.
Classification rules: {classification_rules}
List of notes :
[
\"{"\",\n\"".join(notes_batch)}\"
]
"""
        response=chat(config=self._shared_config, input_items=[{"role": "user", "content": instruction}])
        classified = json.loads(extract_text(response))
        if len(classified) != len(notes_batch):
            raise RuntimeError(f"Number of output elements doesn't match input, {len(notes_batch)} != {len(classified)}")
        return classified
