from __future__ import annotations

import asyncio
import json
from typing import Any

from generic_agent.config import AgentConfig
from generic_agent.logger import log
from generic_agent.utils import resolve_workspace_path

def create_tool_schema_check_ranges(tool_name: str = "check_ranges"):
    return {
        "type": "function",
        "name": tool_name,
        "description": "Validate sensor readings against defined value ranges. Reads JSON files from input directory, checks each sensor's values against validation rules based on sensor type, and writes IDs of sensors with out-of-range values to result file.",
        "parameters": {
            "type": "object",
            "properties": {
                "input_dir": {
                    "type": "string",
                    "description": "Directory path containing sensor JSON files to validate.",
                },
                "result_filepath": {
                    "type": "string",
                    "description": "Output file path where failed sensor IDs will be written (one per line).",
                },
                "validation_rules": {
                    "type": "array",
                    "description": "List of validation rules defining acceptable value ranges per sensor type.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sensor_type": {
                                "type": "string",
                                "description": "Type of sensor this rule applies to (e.g., 'temperature', 'pressure').",
                            },
                            "property_name": {
                                "type": "string",
                                "description": "Name of the property to validate in sensor data (e.g., 'temperature_K').",
                            },
                            "value_min": {
                                "type": "number",
                                "description": "Minimum acceptable value (inclusive).",
                            },
                            "value_max": {
                                "type": "number",
                                "description": "Maximum acceptable value (inclusive).",
                            },
                        },
                        "required": ["sensor_type", "property_name", "value_min", "value_max"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["input_dir", "result_filepath", "validation_rules"],
            "additionalProperties": False,
        },
        "strict": True,
    }

class ToolCheckRanges:
    def __init__(self, shared_config: AgentConfig):
        self._shared_config = shared_config

    async def call(self, params: dict[str, Any]) ->Any:
        if "input_dir" not in params or "result_filepath" not in params or "validation_rules" not in params:
            return { "status": "error: Missing some of required parameters: input_dir or result_filepath or validation_rules" }
        input_dir = params["input_dir"]
        result_filepath = params["result_filepath"]
        validation_rules = params["validation_rules"]

        input_fullpath = resolve_workspace_path(self._shared_config, input_dir)
        result_fullpath = resolve_workspace_path(self._shared_config, result_filepath)

        if not input_fullpath.exists():
            return { "status": f"error: File doesn't exists {input_fullpath}" }

        result_fullpath.parent.mkdir(parents=True, exist_ok=True)

        failed_sensors = []
        for sensor_filepath in input_fullpath.glob("*.json"):
            with sensor_filepath.open() as sensor_file:
                sensor_data = json.load(sensor_file)
                try:
                    if not self._verify_data(sensor_data, validation_rules):
                        failed_sensors.append(sensor_filepath.stem)
                except Exception as ex:
                    sensor_id = sensor_filepath.stem
                    return {
                        "status": f"Validation failed for {sensor_id} with: {ex}",
                        "sensor_id": sensor_id
                    }

        with result_fullpath.open("w") as result_file:
            result_file.write("\n".join(failed_sensors))

        # await asyncio.sleep(0.001)

        status = f"Ranges check done, number of failed sensors: {len(failed_sensors)}"
        log.info(status)
        return {
            "status": status,
            "failed_sensors": len(failed_sensors),
            "result_filepath": result_filepath
        }

    def _verify_data(self, sensor_data, validation_rules):
        if "sensor_type" not in sensor_data:
            raise RuntimeError("Missing sensor_type ")

        current_sensor_types = sensor_data["sensor_type"].split("/")

        for validation_rule in validation_rules:
            if "sensor_type" not in validation_rule:
                raise RuntimeError(f"Validation rule: {validation_rule} is missing `sensor_type` property")
            if "property_name" not in validation_rule:
                raise RuntimeError(f"Validation rule: {validation_rule} is missing `property_name` property")
            if "value_min" not in validation_rule:
                raise RuntimeError(f"Validation rule: {validation_rule} is missing `value_min` property")
            if "value_max" not in validation_rule:
                raise RuntimeError(f"Validation rule: {validation_rule} is missing `value_max` property")
            sensor_type = validation_rule["sensor_type"]
            property_name = validation_rule["property_name"]
            value_min = float(validation_rule["value_min"])
            value_max = float(validation_rule["value_max"])

            if property_name not in sensor_data:
                raise RuntimeError(f"Property: {property_name} missing in sensor data")
            value = float(sensor_data[property_name])

            if sensor_type in current_sensor_types:
                if value_min > value or value_max < value:
                    return False
            elif value != 0.0:
                return False
        return True
