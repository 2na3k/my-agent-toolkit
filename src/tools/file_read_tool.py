"""File reading tool with encoding support."""

import os
import time
from typing import List

from src.core.tools import BaseTool, ToolParameter, ToolResult, ParameterType


class FileReadTool(BaseTool):
    """
    Read file contents with encoding support.

    Supports reading text files with various encodings and provides
    file metadata like size and modification time.
    """

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return (
            "Read file contents with encoding support. "
            "Returns file content, size, and metadata. "
            "Supports UTF-8, ASCII, and other text encodings."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                param_type=ParameterType.STRING,
                description="Path to the file to read",
                required=True,
            ),
            ToolParameter(
                name="encoding",
                param_type=ParameterType.STRING,
                description="File encoding (default: utf-8)",
                required=False,
                default="utf-8",
            ),
            ToolParameter(
                name="max_size",
                param_type=ParameterType.INTEGER,
                description="Maximum file size to read in bytes (default: 10MB)",
                required=False,
                default=10485760,  # 10MB
            ),
        ]

    def execute(self, **kwargs) -> ToolResult:
        """
        Read a file from disk.

        Args:
            path: Path to file
            encoding: Text encoding (default: utf-8)
            max_size: Maximum file size in bytes (default: 10MB)

        Returns:
            ToolResult with file content and metadata
        """
        start_time = time.time()

        # Validate parameters
        is_valid, error = self.validate_parameters(kwargs)
        if not is_valid:
            return ToolResult(
                success=False,
                output=None,
                error=f"Parameter validation failed: {error}",
                execution_time=time.time() - start_time,
            )

        file_path = kwargs["path"]
        encoding = kwargs.get("encoding", "utf-8")
        max_size = kwargs.get("max_size", 10485760)

        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {file_path}",
                    execution_time=time.time() - start_time,
                )

            # Check if it's a file (not a directory)
            if not os.path.isfile(file_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is not a file: {file_path}",
                    execution_time=time.time() - start_time,
                )

            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > max_size:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File too large: {file_size} bytes (max: {max_size} bytes)",
                    execution_time=time.time() - start_time,
                    metadata={"file_size": file_size, "max_size": max_size},
                )

            # Read file
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()

            # Get file metadata
            stat_info = os.stat(file_path)

            execution_time = time.time() - start_time

            return ToolResult(
                success=True,
                output=content,
                error=None,
                execution_time=execution_time,
                metadata={
                    "path": file_path,
                    "size": file_size,
                    "encoding": encoding,
                    "modified_time": stat_info.st_mtime,
                    "line_count": content.count("\n") + 1,
                },
            )

        except UnicodeDecodeError as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Encoding error: Unable to decode file with {encoding} encoding. Try a different encoding.",
                execution_time=execution_time,
                metadata={"path": file_path, "encoding": encoding, "error_type": "UnicodeDecodeError"},
            )

        except PermissionError:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: Cannot read file {file_path}",
                execution_time=execution_time,
                metadata={"path": file_path},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Read error: {str(e)}",
                execution_time=execution_time,
                metadata={"path": file_path, "error_type": type(e).__name__},
            )
