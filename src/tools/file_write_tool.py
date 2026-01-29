"""File writing tool for creating and overwriting files."""

import os
import time
from typing import List

from src.core.tools import BaseTool, ToolParameter, ToolResult, ParameterType


class FileWriteTool(BaseTool):
    """
    Write content to files.

    Creates new files or overwrites existing files with provided content.
    Supports text encoding and automatic directory creation.
    """

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return (
            "Write content to a file. Creates new files or overwrites existing ones. "
            "Automatically creates parent directories if they don't exist. "
            "Use with caution as it will overwrite existing files without warning."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                param_type=ParameterType.STRING,
                description="Path to the file to write",
                required=True,
            ),
            ToolParameter(
                name="content",
                param_type=ParameterType.STRING,
                description="Content to write to the file",
                required=True,
            ),
            ToolParameter(
                name="encoding",
                param_type=ParameterType.STRING,
                description="Text encoding (default: utf-8)",
                required=False,
                default="utf-8",
            ),
            ToolParameter(
                name="create_dirs",
                param_type=ParameterType.BOOLEAN,
                description="Create parent directories if they don't exist (default: True)",
                required=False,
                default=True,
            ),
        ]

    def execute(self, **kwargs) -> ToolResult:
        """
        Write content to a file.

        Args:
            path: Path to file
            content: Content to write
            encoding: Text encoding (default: utf-8)
            create_dirs: Create parent directories (default: True)

        Returns:
            ToolResult with write confirmation
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
        content = kwargs["content"]
        encoding = kwargs.get("encoding", "utf-8")
        create_dirs = kwargs.get("create_dirs", True)

        try:
            # Create parent directories if needed
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                if create_dirs:
                    os.makedirs(parent_dir, exist_ok=True)
                else:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Parent directory does not exist: {parent_dir}",
                        execution_time=time.time() - start_time,
                    )

            # Check if path is a directory
            if os.path.exists(file_path) and os.path.isdir(file_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is a directory, not a file: {file_path}",
                    execution_time=time.time() - start_time,
                )

            # Track if overwriting
            file_existed = os.path.exists(file_path)
            old_size = os.path.getsize(file_path) if file_existed else 0

            # Write file
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)

            # Get new file size
            new_size = os.path.getsize(file_path)

            execution_time = time.time() - start_time

            return ToolResult(
                success=True,
                output=f"Successfully wrote {new_size} bytes to {file_path}",
                error=None,
                execution_time=execution_time,
                metadata={
                    "path": file_path,
                    "size": new_size,
                    "encoding": encoding,
                    "overwritten": file_existed,
                    "old_size": old_size if file_existed else None,
                    "line_count": content.count("\n") + 1,
                },
            )

        except PermissionError:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: Cannot write to {file_path}",
                execution_time=execution_time,
                metadata={"path": file_path},
            )

        except OSError as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"OS error: {str(e)}",
                execution_time=execution_time,
                metadata={"path": file_path, "error_type": "OSError"},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Write error: {str(e)}",
                execution_time=execution_time,
                metadata={"path": file_path, "error_type": type(e).__name__},
            )
