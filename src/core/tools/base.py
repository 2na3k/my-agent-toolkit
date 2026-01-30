"""Base tool class for all tools in the toolkit."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .models import ToolParameter, ToolResult


class BaseTool(ABC):
    """
    Abstract base class for all tools in the toolkit.

    Tools are reusable components that agents can use to perform specific tasks.
    Each tool defines its name, description, parameters, and execution logic.
    """

    def __init__(self):
        """Initialize the base tool."""
        self._validate_definition()

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this tool.

        Returns:
            Tool name (e.g., "web_search", "file_reader")
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human-readable description of what this tool does.

        Returns:
            Description used for tool selection and documentation
        """
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """
        List of parameters this tool accepts.

        Returns:
            List of ToolParameter definitions
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool parameters as keyword arguments

        Returns:
            ToolResult containing execution output or error
        """
        pass

    def validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate parameters against tool's parameter definitions.

        Args:
            params: Dictionary of parameter values

        Returns:
            Tuple of (is_valid, error_message)
        """
        param_map = {p.name: p for p in self.parameters}

        # Check for unknown parameters
        unknown_params = set(params.keys()) - set(param_map.keys())
        if unknown_params:
            return False, f"Unknown parameters: {', '.join(unknown_params)}"

        # Validate each parameter
        for param_def in self.parameters:
            value = params.get(param_def.name)

            # Use default if not provided
            if value is None and param_def.default is not None:
                params[param_def.name] = param_def.default
                value = param_def.default

            is_valid, error = param_def.validate(value)
            if not is_valid:
                return False, error

        return True, None

    def to_openai_schema(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling schema.

        Returns:
            Dictionary following OpenAI function calling format
        """
        # Build properties dict
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_openai_schema()
            if param.required:
                required.append(param.name)

        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                },
            },
        }

        if required:
            schema["function"]["parameters"]["required"] = required

        return schema

    def get_schema(self) -> Dict[str, Any]:
        """
        Alias for to_openai_schema() for consistency.

        Returns:
            Dictionary following OpenAI function calling format
        """
        return self.to_openai_schema()

    def _validate_definition(self):
        """
        Validate that tool is properly defined.

        Raises:
            ValueError: If tool definition is invalid
        """
        if not self.name:
            raise ValueError("Tool must have a name")

        if not self.description:
            raise ValueError(f"Tool '{self.name}' must have a description")

        if not isinstance(self.parameters, list):
            raise ValueError(f"Tool '{self.name}' parameters must be a list")

        # Validate parameter names are unique
        param_names = [p.name for p in self.parameters]
        if len(param_names) != len(set(param_names)):
            raise ValueError(f"Tool '{self.name}' has duplicate parameter names")

    def __repr__(self) -> str:
        """String representation of the tool."""
        return f"{self.__class__.__name__}(name='{self.name}')"
