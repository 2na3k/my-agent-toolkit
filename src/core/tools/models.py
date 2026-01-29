"""Data models for tool framework."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal
from enum import Enum


class ParameterType(str, Enum):
    """Supported parameter types for tools."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """Represents a tool parameter definition."""

    name: str
    param_type: ParameterType
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    items: Optional[Dict[str, Any]] = None  # For array type
    properties: Optional[Dict[str, "ToolParameter"]] = None  # For object type

    def to_openai_schema(self) -> Dict[str, Any]:
        """
        Convert parameter to OpenAI function schema format.

        Returns:
            Dictionary following OpenAI function calling schema
        """
        schema: Dict[str, Any] = {
            "type": self.param_type.value,
            "description": self.description,
        }

        if self.enum:
            schema["enum"] = self.enum

        if self.param_type == ParameterType.ARRAY and self.items:
            schema["items"] = self.items

        if self.param_type == ParameterType.OBJECT and self.properties:
            schema["properties"] = {
                name: param.to_openai_schema()
                for name, param in self.properties.items()
            }
            # Collect required properties
            required_props = [
                name for name, param in self.properties.items() if param.required
            ]
            if required_props:
                schema["required"] = required_props

        return schema

    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a value against this parameter definition.

        Args:
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required
        if value is None:
            if self.required:
                return False, f"Parameter '{self.name}' is required"
            return True, None

        # Type validation
        type_checks = {
            ParameterType.STRING: lambda v: isinstance(v, str),
            ParameterType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            ParameterType.NUMBER: lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            ParameterType.BOOLEAN: lambda v: isinstance(v, bool),
            ParameterType.ARRAY: lambda v: isinstance(v, list),
            ParameterType.OBJECT: lambda v: isinstance(v, dict),
        }

        type_check = type_checks.get(self.param_type)
        if type_check and not type_check(value):
            return False, f"Parameter '{self.name}' must be of type {self.param_type.value}"

        # Enum validation
        if self.enum and value not in self.enum:
            return False, f"Parameter '{self.name}' must be one of {self.enum}"

        # Array items validation
        if self.param_type == ParameterType.ARRAY and self.items and isinstance(value, list):
            item_type = self.items.get("type")
            if item_type:
                for i, item in enumerate(value):
                    if not self._check_type(item, item_type):
                        return False, f"Array item {i} in '{self.name}' must be of type {item_type}"

        # Object properties validation
        if self.param_type == ParameterType.OBJECT and self.properties and isinstance(value, dict):
            for prop_name, prop_param in self.properties.items():
                prop_value = value.get(prop_name)
                is_valid, error = prop_param.validate(prop_value)
                if not is_valid:
                    return False, f"In '{self.name}': {error}"

        return True, None

    @staticmethod
    def _check_type(value: Any, type_str: str) -> bool:
        """Helper to check if value matches type string."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected_type = type_map.get(type_str)
        if expected_type:
            if type_str == "integer":
                return isinstance(value, int) and not isinstance(value, bool)
            elif type_str == "number":
                return isinstance(value, (int, float)) and not isinstance(value, bool)
            return isinstance(value, expected_type)
        return True


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }


@dataclass
class ToolCall:
    """Represents a tool call request."""

    tool_name: str
    parameters: Dict[str, Any]
    call_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool call to dictionary format."""
        result = {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
        }
        if self.call_id:
            result["call_id"] = self.call_id
        if self.context:
            result["context"] = self.context
        return result
