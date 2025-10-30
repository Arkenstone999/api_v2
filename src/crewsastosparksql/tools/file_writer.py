import os
import json
import logging
from datetime import datetime
from typing import Type
from pydantic import BaseModel, Field, validator
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


class FileWriterInput(BaseModel):
    file_path: str = Field(
        ...,
        description="Relative path where to save the file (e.g., 'jobs/my_job/tasks/analysis/analysis.json')",
    )
    content: str = Field(
        ...,
        description="Content to write to the file as a STRING. If you have a dictionary/JSON, convert it to string using json.dumps() first.",
    )
    agent_name: str = Field(
        default="unknown", description="Name of the agent writing the file"
    )

    @validator("file_path")
    def must_be_relative(cls, value: str) -> str:
        if os.path.isabs(value):
            raise ValueError("file_path must be relative to base_dir")

        normalized_path = os.path.normpath(value).replace("\\", "/")
        if normalized_path.startswith("../"):
            raise ValueError("file_path must not escape base_dir (no leading ../)")
        if normalized_path in (".", ""):
            raise ValueError("file_path cannot be empty or '.'")
        return normalized_path


class FileWriterTool(BaseTool):
    name: str = "file_writer"
    description: str = (
        "Writes content to a file. Creates directories if needed. "
        "IMPORTANT: The 'content' parameter MUST be a string. "
        "If you have a Python dictionary or JSON object, convert it to a string first using json.dumps(your_dict). "
        "Example: file_writer(file_path='jobs/test/output.json', content=json.dumps({'key': 'value'}), agent_name='my_agent')"
    )
    args_schema: Type[BaseModel] = FileWriterInput
    base_dir: str = Field(default=".")

    def _run(self, file_path: str, content: str, agent_name: str = "unknown") -> str:
        try:
            absolute_base_dir = os.path.abspath(self.base_dir)
            os.makedirs(absolute_base_dir, exist_ok=True)

            normalized_relative_path = os.path.normpath(file_path)
            absolute_file_path = os.path.abspath(
                os.path.join(absolute_base_dir, normalized_relative_path)
            )

            if (
                not os.path.commonpath([absolute_file_path, absolute_base_dir])
                == absolute_base_dir
            ):
                return "Error writing file: resolved path escapes base_dir"

            parent_directory = os.path.dirname(absolute_file_path)
            if parent_directory:
                os.makedirs(parent_directory, exist_ok=True)

            if not content or content.strip() == "":
                placeholder_data = {
                    "status": "empty_output",
                    "agent": agent_name,
                    "timestamp": datetime.now().isoformat(),
                    "note": "This output was empty and a placeholder was generated",
                }
                content = json.dumps(placeholder_data, indent=2)
                logger.warning(
                    f"Empty output detected from {agent_name}, writing placeholder to {absolute_file_path}"
                )

            with open(absolute_file_path, "w", encoding="utf-8") as file_handle:
                file_handle.write(content)

            logger.info(
                f"File written successfully by {agent_name}: {absolute_file_path}"
            )
            print(f"[{agent_name}] WROTE: {absolute_file_path}")

            self._write_step_log(absolute_file_path, agent_name)

            return f"SUCCESS: File written to {absolute_file_path}"
        except Exception as error:
            error_message = f"Error writing file: {error!s}"
            logger.error(f"[{agent_name}] {error_message}")
            return error_message

    def _write_step_log(self, file_path: str, agent_name: str):
        try:
            path_components = file_path.split(os.sep)
            if "tasks" in path_components:
                tasks_index = path_components.index("tasks")
                if tasks_index + 1 < len(path_components):
                    step_name = path_components[tasks_index + 1]
                    if "jobs" in path_components and path_components.index(
                        "jobs"
                    ) + 1 < len(path_components):
                        jobs_index = path_components.index("jobs")

                        logs_directory = os.path.join(
                            os.sep.join(path_components[: jobs_index + 2]), "logs"
                        )
                        os.makedirs(logs_directory, exist_ok=True)

                        log_file_path = os.path.join(logs_directory, f"{step_name}.log")
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_entry = f"[{timestamp}] [{agent_name}] Wrote: {file_path}\n"

                        with open(log_file_path, "a", encoding="utf-8") as log_file:
                            log_file.write(log_entry)
        except Exception as error:
            logger.warning(f"Could not write step log: {error}")
