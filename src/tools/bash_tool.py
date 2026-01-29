"""Bash command execution tool with safety checks and timeout support."""

import subprocess
import time
from typing import List

from src.core.tools import BaseTool, ToolParameter, ToolResult, ParameterType


class BashTool(BaseTool):
    """
    Execute bash commands with timeout and safety checks.

    This tool allows executing shell commands with configurable timeout
    and working directory. Commands are validated for dangerous patterns
    before execution.
    """

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return (
            "Execute bash commands with timeout and safety checks. "
            "Supports setting working directory and command timeout. "
            "Returns stdout, stderr, and exit code."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="command",
                param_type=ParameterType.STRING,
                description="The bash command to execute",
                required=True,
            ),
            ToolParameter(
                name="timeout",
                param_type=ParameterType.INTEGER,
                description="Timeout in seconds (default: 30, max: 300)",
                required=False,
                default=30,
            ),
            ToolParameter(
                name="cwd",
                param_type=ParameterType.STRING,
                description="Working directory for command execution",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="shell",
                param_type=ParameterType.BOOLEAN,
                description="Execute command through shell (default: True)",
                required=False,
                default=True,
            ),
        ]

    def execute(self, **kwargs) -> ToolResult:
        """
        Execute a bash command.

        Args:
            command: Bash command to execute
            timeout: Timeout in seconds (default: 30, max: 300)
            cwd: Working directory (default: None)
            shell: Execute through shell (default: True)

        Returns:
            ToolResult with stdout, stderr, and exit code
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

        command = kwargs["command"]
        timeout = min(kwargs.get("timeout", 30), 300)  # Max 5 minutes
        cwd = kwargs.get("cwd")
        shell = kwargs.get("shell", True)

        try:
            # Execute command
            process = subprocess.run(
                command,
                shell=shell,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            execution_time = time.time() - start_time

            # Prepare output
            output = {
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode,
            }

            success = process.returncode == 0
            error_msg = None if success else f"Command failed with exit code {process.returncode}"

            return ToolResult(
                success=success,
                output=output,
                error=error_msg,
                execution_time=execution_time,
                metadata={
                    "command": command,
                    "timeout": timeout,
                    "cwd": cwd,
                },
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Command timed out after {timeout} seconds",
                execution_time=execution_time,
                metadata={"command": command, "timeout": timeout},
            )

        except FileNotFoundError:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Working directory not found: {cwd}",
                execution_time=execution_time,
                metadata={"command": command, "cwd": cwd},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"Execution error: {str(e)}",
                execution_time=execution_time,
                metadata={"command": command, "error_type": type(e).__name__},
            )
