"""Tool executor for running tools with safety and timing."""

import time
from typing import Dict, Any, Optional, List

from ..logger import get_logger
from .base import BaseTool
from .models import ToolCall, ToolResult
from .registry import ToolRegistry
from .safety import SafetyValidator


class ToolExecutor:
    """
    Executes tools with validation, safety checks, and timing.

    Provides centralized tool execution with:
    - Parameter validation
    - Safety checking
    - Execution timing
    - Error handling
    - Logging
    """

    def __init__(
        self,
        safety_enabled: bool = True,
        allow_warnings: bool = True,
        timeout: Optional[float] = None,
    ):
        """
        Initialize the tool executor.

        Args:
            safety_enabled: Enable safety validation
            allow_warnings: Allow execution with warnings (if False, warnings block execution)
            timeout: Optional timeout in seconds for tool execution
        """
        self.safety_enabled = safety_enabled
        self.allow_warnings = allow_warnings
        self.timeout = timeout
        self.logger = get_logger("tool.executor")

        # Initialize safety validator
        self.safety_validator = SafetyValidator() if safety_enabled else None

        # Execution statistics
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "blocked_executions": 0,
            "total_execution_time": 0.0,
        }

    def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """
        Execute a tool with given parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters as dictionary
            context: Optional context information

        Returns:
            ToolResult containing execution output or error
        """
        start_time = time.time()
        self.stats["total_executions"] += 1

        try:
            # Get tool instance
            tool = self._get_tool(tool_name)
            if isinstance(tool, ToolResult):  # Error occurred
                self.stats["failed_executions"] += 1
                return tool

            # Validate parameters
            is_valid, error = tool.validate_parameters(parameters)
            if not is_valid:
                self.logger.error(
                    f"Parameter validation failed for '{tool_name}': {error}"
                )
                self.stats["failed_executions"] += 1
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Parameter validation failed: {error}",
                    execution_time=time.time() - start_time,
                )

            # Safety validation
            if self.safety_enabled and self.safety_validator:
                is_safe, violations = self.safety_validator.validate_parameters(
                    tool_name, parameters, self.allow_warnings
                )
                if not is_safe:
                    self.logger.error(
                        f"Safety validation failed for '{tool_name}': {violations}"
                    )
                    self.stats["blocked_executions"] += 1
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Safety validation failed: {'; '.join(violations)}",
                        execution_time=time.time() - start_time,
                        metadata={"safety_violations": violations},
                    )
                elif violations:
                    # Log warnings even if execution proceeds
                    self.logger.warning(
                        f"Safety warnings for '{tool_name}': {violations}"
                    )

            # Execute tool
            self.logger.info(f"Executing tool: {tool_name}")
            self.logger.debug(f"Parameters: {parameters}")

            try:
                result = tool.execute(**parameters)

                # Ensure result is ToolResult
                if not isinstance(result, ToolResult):
                    result = ToolResult(success=True, output=result)

                # Add execution time
                execution_time = time.time() - start_time
                result.execution_time = execution_time

                # Update stats
                if result.success:
                    self.stats["successful_executions"] += 1
                else:
                    self.stats["failed_executions"] += 1

                self.stats["total_execution_time"] += execution_time

                self.logger.info(
                    f"Tool '{tool_name}' completed in {execution_time:.3f}s "
                    f"(success={result.success})"
                )

                return result

            except Exception as e:
                self.logger.error(f"Tool execution failed: {e}", exc_info=True)
                self.stats["failed_executions"] += 1
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Execution error: {str(e)}",
                    execution_time=time.time() - start_time,
                )

        except Exception as e:
            self.logger.error(f"Unexpected error in executor: {e}", exc_info=True)
            self.stats["failed_executions"] += 1
            return ToolResult(
                success=False,
                output=None,
                error=f"Executor error: {str(e)}",
                execution_time=time.time() - start_time,
            )

    def execute_batch(
        self, tool_calls: List[ToolCall], stop_on_error: bool = False
    ) -> List[ToolResult]:
        """
        Execute multiple tools in sequence.

        Args:
            tool_calls: List of ToolCall objects to execute
            stop_on_error: Stop execution if a tool fails

        Returns:
            List of ToolResult objects
        """
        results = []

        for tool_call in tool_calls:
            self.logger.info(
                f"Executing batch tool {len(results) + 1}/{len(tool_calls)}: "
                f"{tool_call.tool_name}"
            )

            result = self.execute(
                tool_name=tool_call.tool_name,
                parameters=tool_call.parameters,
                context=tool_call.context,
            )

            results.append(result)

            if stop_on_error and not result.success:
                self.logger.warning(
                    f"Batch execution stopped due to error in '{tool_call.tool_name}'"
                )
                break

        return results

    def _get_tool(self, tool_name: str) -> BaseTool | ToolResult:
        """
        Get tool instance from registry.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool instance or ToolResult with error
        """
        try:
            return ToolRegistry.create(tool_name)
        except ValueError as e:
            self.logger.error(f"Tool not found: {tool_name}")
            return ToolResult(
                success=False, output=None, error=f"Tool not found: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Failed to create tool '{tool_name}': {e}")
            return ToolResult(
                success=False, output=None, error=f"Tool creation failed: {str(e)}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dictionary of execution statistics
        """
        stats = self.stats.copy()

        # Add computed metrics
        if stats["total_executions"] > 0:
            stats["success_rate"] = (
                stats["successful_executions"] / stats["total_executions"]
            )
            stats["failure_rate"] = (
                stats["failed_executions"] / stats["total_executions"]
            )
            stats["blocked_rate"] = (
                stats["blocked_executions"] / stats["total_executions"]
            )
            stats["avg_execution_time"] = (
                stats["total_execution_time"] / stats["total_executions"]
            )
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
            stats["blocked_rate"] = 0.0
            stats["avg_execution_time"] = 0.0

        return stats

    def reset_stats(self):
        """Reset execution statistics."""
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "blocked_executions": 0,
            "total_execution_time": 0.0,
        }
        self.logger.info("Execution statistics reset")

    def enable_safety(self, allow_warnings: bool = True):
        """
        Enable safety validation.

        Args:
            allow_warnings: Allow execution with warnings
        """
        self.safety_enabled = True
        self.allow_warnings = allow_warnings
        if not self.safety_validator:
            self.safety_validator = SafetyValidator()
        self.logger.info(f"Safety validation enabled (allow_warnings={allow_warnings})")

    def disable_safety(self):
        """Disable safety validation. Use with caution!"""
        self.safety_enabled = False
        self.logger.warning("Safety validation disabled - use with caution!")
