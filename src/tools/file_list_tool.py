"""File listing tool for directory exploration."""

import os
import time
from typing import List

from src.core.tools import BaseTool, ToolParameter, ToolResult, ParameterType


class FileListTool(BaseTool):
    """
    List directory contents with filtering options.

    Lists files and directories with metadata like size, modification time,
    and file type. Supports filtering by pattern and recursive listing.
    """

    @property
    def name(self) -> str:
        return "file_list"

    @property
    def description(self) -> str:
        return (
            "List contents of a directory with file metadata. "
            "Supports filtering by pattern, recursive listing, and "
            "shows file size, type, and modification time."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                param_type=ParameterType.STRING,
                description="Path to the directory to list (default: current directory)",
                required=False,
                default=".",
            ),
            ToolParameter(
                name="pattern",
                param_type=ParameterType.STRING,
                description="Glob pattern to filter files (e.g., '*.py', '*.txt')",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="recursive",
                param_type=ParameterType.BOOLEAN,
                description="Recursively list subdirectories (default: False)",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="include_hidden",
                param_type=ParameterType.BOOLEAN,
                description="Include hidden files (starting with .) (default: False)",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="max_depth",
                param_type=ParameterType.INTEGER,
                description="Maximum depth for recursive listing (default: 3)",
                required=False,
                default=3,
            ),
        ]

    def execute(self, **kwargs) -> ToolResult:
        """
        List directory contents.

        Args:
            path: Directory path (default: current directory)
            pattern: Glob pattern filter (e.g., '*.py')
            recursive: Recursively list subdirectories (default: False)
            include_hidden: Include hidden files (default: False)
            max_depth: Maximum recursion depth (default: 3)

        Returns:
            ToolResult with list of files and metadata
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

        dir_path = kwargs.get("path", ".")
        pattern = kwargs.get("pattern")
        recursive = kwargs.get("recursive", False)
        include_hidden = kwargs.get("include_hidden", False)
        max_depth = kwargs.get("max_depth", 3)

        try:
            # Check if directory exists
            if not os.path.exists(dir_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Directory not found: {dir_path}",
                    execution_time=time.time() - start_time,
                )

            # Check if it's a directory
            if not os.path.isdir(dir_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is not a directory: {dir_path}",
                    execution_time=time.time() - start_time,
                )

            # List files
            files = []

            if recursive:
                files = self._list_recursive(
                    dir_path, pattern, include_hidden, max_depth, current_depth=0
                )
            else:
                files = self._list_single(dir_path, pattern, include_hidden)

            execution_time = time.time() - start_time

            # Summary statistics
            file_count = sum(1 for f in files if f["type"] == "file")
            dir_count = sum(1 for f in files if f["type"] == "directory")
            total_size = sum(f["size"] for f in files if f["type"] == "file")

            return ToolResult(
                success=True,
                output=files,
                error=None,
                execution_time=execution_time,
                metadata={
                    "path": dir_path,
                    "file_count": file_count,
                    "directory_count": dir_count,
                    "total_size": total_size,
                    "recursive": recursive,
                    "pattern": pattern,
                },
            )

        except PermissionError:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: Cannot access directory {dir_path}",
                execution_time=execution_time,
                metadata={"path": dir_path},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"List error: {str(e)}",
                execution_time=execution_time,
                metadata={"path": dir_path, "error_type": type(e).__name__},
            )

    def _list_single(self, dir_path: str, pattern: str | None, include_hidden: bool) -> List[dict]:
        """List files in a single directory."""
        import fnmatch

        files = []

        for entry in os.listdir(dir_path):
            # Skip hidden files if not included
            if not include_hidden and entry.startswith("."):
                continue

            # Apply pattern filter
            if pattern and not fnmatch.fnmatch(entry, pattern):
                continue

            full_path = os.path.join(dir_path, entry)

            try:
                stat_info = os.stat(full_path)
                is_dir = os.path.isdir(full_path)

                files.append({
                    "name": entry,
                    "path": full_path,
                    "type": "directory" if is_dir else "file",
                    "size": stat_info.st_size if not is_dir else 0,
                    "modified": stat_info.st_mtime,
                })
            except (PermissionError, OSError):
                # Skip files we can't access
                continue

        return files

    def _list_recursive(
        self,
        dir_path: str,
        pattern: str | None,
        include_hidden: bool,
        max_depth: int,
        current_depth: int = 0,
    ) -> List[dict]:
        """Recursively list files in directory tree."""
        import fnmatch

        if current_depth >= max_depth:
            return []

        files = []

        try:
            for entry in os.listdir(dir_path):
                # Skip hidden files if not included
                if not include_hidden and entry.startswith("."):
                    continue

                full_path = os.path.join(dir_path, entry)

                try:
                    stat_info = os.stat(full_path)
                    is_dir = os.path.isdir(full_path)

                    # Check pattern match
                    matches_pattern = not pattern or fnmatch.fnmatch(entry, pattern)

                    if matches_pattern or is_dir:
                        files.append({
                            "name": entry,
                            "path": full_path,
                            "type": "directory" if is_dir else "file",
                            "size": stat_info.st_size if not is_dir else 0,
                            "modified": stat_info.st_mtime,
                            "depth": current_depth,
                        })

                    # Recurse into subdirectories
                    if is_dir:
                        sub_files = self._list_recursive(
                            full_path, pattern, include_hidden, max_depth, current_depth + 1
                        )
                        files.extend(sub_files)

                except (PermissionError, OSError):
                    # Skip files/dirs we can't access
                    continue

        except PermissionError:
            # Skip directories we can't access
            pass

        return files
