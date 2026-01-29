"""Built-in tools for the agent toolkit.

This module provides a collection of built-in tools that agents can use
to interact with the system, files, and execute commands.

Available Tools:
- bash: Execute bash commands with timeout and safety checks
- file_read: Read file contents with encoding support
- file_write: Write content to files (create or overwrite)
- file_edit: Search and replace text in files
- file_list: List directory contents with metadata
- grep: Search for patterns in file contents

All tools are automatically registered with the ToolRegistry when this
module is imported.
"""

from src.core.tools import register_tool

# Import all tool classes
from .bash_tool import BashTool
from .file_read_tool import FileReadTool
from .file_write_tool import FileWriteTool
from .file_edit_tool import FileEditTool
from .file_list_tool import FileListTool
from .grep_tool import GrepTool


# Register all tools
@register_tool(
    category="system",
    tags=["bash", "command", "execution", "shell"],
    enabled=True,
    dangerous=True,  # Marked as dangerous due to command execution
)
class RegisteredBashTool(BashTool):
    """Registered Bash tool."""
    pass


@register_tool(
    category="filesystem",
    tags=["file", "read", "io"],
    enabled=True,
    dangerous=False,
)
class RegisteredFileReadTool(FileReadTool):
    """Registered File Read tool."""
    pass


@register_tool(
    category="filesystem",
    tags=["file", "write", "io"],
    enabled=True,
    dangerous=True,  # Marked as dangerous due to file modification
)
class RegisteredFileWriteTool(FileWriteTool):
    """Registered File Write tool."""
    pass


@register_tool(
    category="filesystem",
    tags=["file", "edit", "modify", "search", "replace"],
    enabled=True,
    dangerous=True,  # Marked as dangerous due to file modification
)
class RegisteredFileEditTool(FileEditTool):
    """Registered File Edit tool."""
    pass


@register_tool(
    category="filesystem",
    tags=["file", "list", "directory", "ls"],
    enabled=True,
    dangerous=False,
)
class RegisteredFileListTool(FileListTool):
    """Registered File List tool."""
    pass


@register_tool(
    category="search",
    tags=["grep", "search", "find", "pattern"],
    enabled=True,
    dangerous=False,
)
class RegisteredGrepTool(GrepTool):
    """Registered Grep tool."""
    pass


# Export original tool classes
__all__ = [
    "BashTool",
    "FileReadTool",
    "FileWriteTool",
    "FileEditTool",
    "FileListTool",
    "GrepTool",
]
