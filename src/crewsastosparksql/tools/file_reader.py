import os
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class FileReaderInput(BaseModel):
    file_path: str = Field(
        ..., description="Absolute or relative path to the file to read"
    )


class FileReaderTool(BaseTool):
    name: str = "file_reader"
    description: str = (
        "Reads the content of a file (SAS, SQL, Python, etc.) and returns its content. "
        "Use this to read the input SAS file or any other file you need to analyze."
    )
    args_schema: Type[BaseModel] = FileReaderInput

    def _run(self, file_path: str) -> str:
        """Read and return the content of a file."""
        try:
            # Handle both absolute and relative paths
            if not os.path.isabs(file_path):
                # Try relative to current working directory
                abs_path = os.path.abspath(file_path)
            else:
                abs_path = file_path

            # Check if file exists
            if not os.path.exists(abs_path):
                return f"ERROR: File not found at {abs_path}"

            # Check if file is readable
            if not os.path.isfile(abs_path):
                return f"ERROR: Path is not a file: {abs_path}"

            # Read the file content
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content or content.strip() == "":
                return f"WARNING: File is empty at {abs_path}"

            return f"File content from {abs_path}:\n\n{content}"

        except PermissionError:
            return f"ERROR: Permission denied reading file: {file_path}"
        except UnicodeDecodeError:
            # Try reading as binary and return info
            try:
                with open(abs_path, "rb") as f:
                    size = len(f.read())
                return f"ERROR: File appears to be binary (size: {size} bytes). Cannot read as text."
            except Exception as e:
                return f"ERROR: Cannot read file: {e}"
        except Exception as e:
            return f"ERROR: Unexpected error reading file: {e}"
