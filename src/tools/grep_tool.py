"""Grep tool for searching file contents."""

import os
import re
import time
from typing import List

from src.core.tools import BaseTool, ToolParameter, ToolResult, ParameterType


class GrepTool(BaseTool):
    """
    Search for patterns in file contents.

    Searches files for text patterns with support for regex, case-insensitive
    search, and recursive directory search. Returns matching lines with
    line numbers and context.
    """

    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return (
            "Search for text patterns in files. Supports regex patterns, "
            "case-insensitive search, and recursive directory search. "
            "Returns matching lines with line numbers and optional context."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="pattern",
                param_type=ParameterType.STRING,
                description="Text pattern to search for (literal or regex)",
                required=True,
            ),
            ToolParameter(
                name="path",
                param_type=ParameterType.STRING,
                description="File or directory path to search in",
                required=True,
            ),
            ToolParameter(
                name="regex",
                param_type=ParameterType.BOOLEAN,
                description="Use regex pattern matching (default: False)",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="case_sensitive",
                param_type=ParameterType.BOOLEAN,
                description="Case-sensitive search (default: True)",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="recursive",
                param_type=ParameterType.BOOLEAN,
                description="Recursively search subdirectories (default: False)",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="file_pattern",
                param_type=ParameterType.STRING,
                description="Filter files by glob pattern (e.g., '*.py')",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="context_lines",
                param_type=ParameterType.INTEGER,
                description="Number of context lines before/after match (default: 0)",
                required=False,
                default=0,
            ),
            ToolParameter(
                name="max_matches",
                param_type=ParameterType.INTEGER,
                description="Maximum number of matches to return (default: 100)",
                required=False,
                default=100,
            ),
        ]

    def execute(self, **kwargs) -> ToolResult:
        """
        Search for patterns in files.

        Args:
            pattern: Search pattern (literal or regex)
            path: File or directory to search
            regex: Use regex matching (default: False)
            case_sensitive: Case-sensitive search (default: True)
            recursive: Recursively search directories (default: False)
            file_pattern: Filter files by pattern (e.g., '*.py')
            context_lines: Lines of context around matches (default: 0)
            max_matches: Maximum matches to return (default: 100)

        Returns:
            ToolResult with list of matches
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

        search_pattern = kwargs["pattern"]
        search_path = kwargs["path"]
        use_regex = kwargs.get("regex", False)
        case_sensitive = kwargs.get("case_sensitive", True)
        recursive = kwargs.get("recursive", False)
        file_pattern = kwargs.get("file_pattern")
        context_lines = kwargs.get("context_lines", 0)
        max_matches = kwargs.get("max_matches", 100)

        try:
            # Check if path exists
            if not os.path.exists(search_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path not found: {search_path}",
                    execution_time=time.time() - start_time,
                )

            # Compile search pattern
            if use_regex:
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    compiled_pattern = re.compile(search_pattern, flags)
                except re.error as e:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Invalid regex pattern: {str(e)}",
                        execution_time=time.time() - start_time,
                    )
            else:
                # Escape for literal matching
                escaped = re.escape(search_pattern)
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled_pattern = re.compile(escaped, flags)

            # Collect files to search
            files_to_search = []
            if os.path.isfile(search_path):
                files_to_search = [search_path]
            elif os.path.isdir(search_path):
                files_to_search = self._collect_files(search_path, file_pattern, recursive)

            # Search files
            matches = []
            total_matches = 0
            files_searched = 0

            for file_path in files_to_search:
                if total_matches >= max_matches:
                    break

                file_matches = self._search_file(
                    file_path,
                    compiled_pattern,
                    context_lines,
                    max_matches - total_matches,
                )

                if file_matches:
                    files_searched += 1
                    matches.extend(file_matches)
                    total_matches += len(file_matches)

            execution_time = time.time() - start_time

            return ToolResult(
                success=True,
                output=matches,
                error=None,
                execution_time=execution_time,
                metadata={
                    "pattern": search_pattern,
                    "path": search_path,
                    "total_matches": total_matches,
                    "files_with_matches": files_searched,
                    "files_searched": len(files_to_search),
                    "regex": use_regex,
                    "case_sensitive": case_sensitive,
                    "truncated": total_matches >= max_matches,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Search error: {str(e)}",
                execution_time=execution_time,
                metadata={"path": search_path, "error_type": type(e).__name__},
            )

    def _collect_files(
        self, dir_path: str, file_pattern: str | None, recursive: bool
    ) -> List[str]:
        """Collect files to search."""
        import fnmatch

        files = []

        if recursive:
            for root, _, filenames in os.walk(dir_path):
                for filename in filenames:
                    if file_pattern and not fnmatch.fnmatch(filename, file_pattern):
                        continue
                    files.append(os.path.join(root, filename))
        else:
            try:
                for entry in os.listdir(dir_path):
                    full_path = os.path.join(dir_path, entry)
                    if os.path.isfile(full_path):
                        if file_pattern and not fnmatch.fnmatch(entry, file_pattern):
                            continue
                        files.append(full_path)
            except PermissionError:
                pass

        return files

    def _search_file(
        self, file_path: str, pattern: re.Pattern, context_lines: int, max_matches: int
    ) -> List[dict]:
        """Search a single file for pattern matches."""
        matches = []

        try:
            # Try to read as text file
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Search each line
            for line_num, line in enumerate(lines, start=1):
                if len(matches) >= max_matches:
                    break

                if pattern.search(line):
                    # Collect context lines
                    start_line = max(0, line_num - 1 - context_lines)
                    end_line = min(len(lines), line_num + context_lines)

                    context = {
                        "before": [
                            lines[i].rstrip() for i in range(start_line, line_num - 1)
                        ],
                        "after": [
                            lines[i].rstrip() for i in range(line_num, end_line)
                        ],
                    }

                    matches.append({
                        "file": file_path,
                        "line_number": line_num,
                        "line": line.rstrip(),
                        "context": context if context_lines > 0 else None,
                    })

        except (PermissionError, UnicodeDecodeError, OSError):
            # Skip files we can't read
            pass

        return matches
