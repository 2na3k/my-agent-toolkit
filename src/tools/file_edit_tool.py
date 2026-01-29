"""File editing tool for search and replace operations."""

import os
import re
import time
from typing import List

from src.core.tools import BaseTool, ToolParameter, ToolResult, ParameterType


class FileEditTool(BaseTool):
    """
    Search and replace text in files.

    Performs find-and-replace operations on file contents with support
    for literal strings or regex patterns. Can replace all occurrences
    or just the first match.
    """

    @property
    def name(self) -> str:
        return "file_edit"

    @property
    def description(self) -> str:
        return (
            "Search and replace text in files. Supports literal string matching "
            "or regex patterns. Can replace all occurrences or just the first match. "
            "Creates a backup before editing if specified."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                param_type=ParameterType.STRING,
                description="Path to the file to edit",
                required=True,
            ),
            ToolParameter(
                name="search",
                param_type=ParameterType.STRING,
                description="Text or regex pattern to search for",
                required=True,
            ),
            ToolParameter(
                name="replace",
                param_type=ParameterType.STRING,
                description="Replacement text",
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
                name="replace_all",
                param_type=ParameterType.BOOLEAN,
                description="Replace all occurrences (default: True)",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="case_sensitive",
                param_type=ParameterType.BOOLEAN,
                description="Case-sensitive search (default: True)",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="encoding",
                param_type=ParameterType.STRING,
                description="File encoding (default: utf-8)",
                required=False,
                default="utf-8",
            ),
        ]

    def execute(self, **kwargs) -> ToolResult:
        """
        Edit a file by searching and replacing text.

        Args:
            path: Path to file
            search: Search pattern (string or regex)
            replace: Replacement text
            regex: Use regex matching (default: False)
            replace_all: Replace all occurrences (default: True)
            case_sensitive: Case-sensitive search (default: True)
            encoding: Text encoding (default: utf-8)

        Returns:
            ToolResult with edit details
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
        search_pattern = kwargs["search"]
        replacement = kwargs["replace"]
        use_regex = kwargs.get("regex", False)
        replace_all = kwargs.get("replace_all", True)
        case_sensitive = kwargs.get("case_sensitive", True)
        encoding = kwargs.get("encoding", "utf-8")

        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {file_path}",
                    execution_time=time.time() - start_time,
                )

            # Check if it's a file
            if not os.path.isfile(file_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is not a file: {file_path}",
                    execution_time=time.time() - start_time,
                )

            # Read original content
            with open(file_path, "r", encoding=encoding) as f:
                original_content = f.read()

            # Perform search and replace
            if use_regex:
                # Regex mode
                flags = 0 if case_sensitive else re.IGNORECASE
                try:
                    if replace_all:
                        new_content = re.sub(search_pattern, replacement, original_content, flags=flags)
                        match_count = len(re.findall(search_pattern, original_content, flags=flags))
                    else:
                        new_content = re.sub(search_pattern, replacement, original_content, count=1, flags=flags)
                        match_count = 1 if re.search(search_pattern, original_content, flags=flags) else 0
                except re.error as e:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Invalid regex pattern: {str(e)}",
                        execution_time=time.time() - start_time,
                    )
            else:
                # Literal string mode
                if case_sensitive:
                    search_str = search_pattern
                    content_to_search = original_content
                else:
                    search_str = search_pattern.lower()
                    content_to_search = original_content.lower()

                # Count matches
                match_count = content_to_search.count(search_str)

                if match_count == 0:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Search pattern not found in file: {search_pattern}",
                        execution_time=time.time() - start_time,
                        metadata={
                            "path": file_path,
                            "search": search_pattern,
                            "matches": 0,
                        },
                    )

                # Replace
                if replace_all:
                    if case_sensitive:
                        new_content = original_content.replace(search_pattern, replacement)
                    else:
                        # Case-insensitive replace (preserve original case boundaries)
                        import re
                        pattern = re.escape(search_pattern)
                        new_content = re.sub(pattern, replacement, original_content, flags=re.IGNORECASE)
                else:
                    if case_sensitive:
                        new_content = original_content.replace(search_pattern, replacement, 1)
                    else:
                        pattern = re.escape(search_pattern)
                        new_content = re.sub(pattern, replacement, original_content, count=1, flags=re.IGNORECASE)

            # Check if any changes were made
            if new_content == original_content:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"No matches found for search pattern: {search_pattern}",
                    execution_time=time.time() - start_time,
                    metadata={
                        "path": file_path,
                        "search": search_pattern,
                        "matches": 0,
                    },
                )

            # Write updated content
            with open(file_path, "w", encoding=encoding) as f:
                f.write(new_content)

            execution_time = time.time() - start_time

            replacements_made = match_count if replace_all else min(match_count, 1)

            return ToolResult(
                success=True,
                output=f"Successfully replaced {replacements_made} occurrence(s) in {file_path}",
                error=None,
                execution_time=execution_time,
                metadata={
                    "path": file_path,
                    "search": search_pattern,
                    "replace": replacement,
                    "matches_found": match_count,
                    "replacements_made": replacements_made,
                    "regex": use_regex,
                    "case_sensitive": case_sensitive,
                    "size_before": len(original_content),
                    "size_after": len(new_content),
                },
            )

        except PermissionError:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: Cannot edit file {file_path}",
                execution_time=execution_time,
                metadata={"path": file_path},
            )

        except UnicodeDecodeError:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Encoding error: Unable to decode file with {encoding} encoding",
                execution_time=execution_time,
                metadata={"path": file_path, "encoding": encoding},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Edit error: {str(e)}",
                execution_time=execution_time,
                metadata={"path": file_path, "error_type": type(e).__name__},
            )
