"""Tool registry for managing and discovering tools."""

from typing import Dict, List, Optional, Type, Callable, Any
import functools

from ..logger import get_logger
from .base import BaseTool


class ToolRegistry:
    """
    Registry for managing tool instances and metadata.

    Similar to AgentFactory, this provides centralized tool management with:
    - Tool registration and discovery
    - Metadata storage
    - Tool instantiation
    """

    _tools: Dict[str, Type[BaseTool]] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}
    _logger = get_logger("tool.registry")

    @classmethod
    def register(
        cls,
        tool_class: Type[BaseTool],
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        enabled: bool = True,
        **metadata,
    ):
        """
        Register a tool class with metadata.

        Args:
            tool_class: Tool class to register (must inherit from BaseTool)
            category: Tool category (e.g., "web", "file", "data")
            tags: List of tags for tool discovery
            enabled: Whether tool is enabled for use
            **metadata: Additional metadata to store
        """
        if not issubclass(tool_class, BaseTool):
            raise TypeError(f"{tool_class.__name__} must inherit from BaseTool")

        # Create instance to get name
        try:
            instance = tool_class()
            tool_name = instance.name
        except Exception as e:
            cls._logger.error(f"Failed to instantiate {tool_class.__name__}: {e}")
            raise

        # Check for duplicate registration
        if tool_name in cls._tools:
            cls._logger.warning(
                f"Tool '{tool_name}' already registered, overwriting with {tool_class.__name__}"
            )

        # Register tool class
        cls._tools[tool_name] = tool_class

        # Store metadata
        tool_metadata = {
            "tool_class": tool_class.__name__,
            "category": category,
            "tags": tags or [],
            "enabled": enabled,
            "description": instance.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.param_type.value,
                    "description": p.description,
                    "required": p.required,
                }
                for p in instance.parameters
            ],
            **metadata,
        }
        cls._metadata[tool_name] = tool_metadata

        cls._logger.info(
            f"Registered tool: {tool_name} "
            f"(class={tool_class.__name__}, category={category}, enabled={enabled})"
        )

    @classmethod
    def create(cls, tool_name: str) -> BaseTool:
        """
        Create a tool instance by name.

        Args:
            tool_name: Name of the tool to create

        Returns:
            Instance of the requested tool

        Raises:
            ValueError: If tool not found or disabled
        """
        if tool_name not in cls._tools:
            available = ", ".join(cls._tools.keys())
            raise ValueError(
                f"Tool '{tool_name}' not found. Available tools: {available}"
            )

        metadata = cls._metadata.get(tool_name, {})
        if not metadata.get("enabled", True):
            raise ValueError(f"Tool '{tool_name}' is disabled")

        tool_class = cls._tools[tool_name]
        try:
            instance = tool_class()
            cls._logger.debug(f"Created tool instance: {tool_name}")
            return instance
        except Exception as e:
            cls._logger.error(f"Failed to create tool '{tool_name}': {e}")
            raise

    @classmethod
    def get_metadata(cls, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool metadata dictionary or None if not found
        """
        return cls._metadata.get(tool_name)

    @classmethod
    def get_all_metadata(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all registered tools.

        Returns:
            Dictionary mapping tool names to metadata
        """
        return cls._metadata.copy()

    @classmethod
    def list_tools(cls, enabled_only: bool = True) -> List[str]:
        """
        List all registered tool names.

        Args:
            enabled_only: Only return enabled tools

        Returns:
            List of tool names
        """
        if enabled_only:
            return [
                name
                for name, meta in cls._metadata.items()
                if meta.get("enabled", True)
            ]
        return list(cls._tools.keys())

    @classmethod
    def get_by_category(cls, category: str, enabled_only: bool = True) -> List[str]:
        """
        Get tools by category.

        Args:
            category: Category to filter by
            enabled_only: Only return enabled tools

        Returns:
            List of tool names in the category
        """
        tools = []
        for name, meta in cls._metadata.items():
            if enabled_only and not meta.get("enabled", True):
                continue
            if meta.get("category") == category:
                tools.append(name)
        return tools

    @classmethod
    def get_by_tag(cls, tag: str, enabled_only: bool = True) -> List[str]:
        """
        Get tools by tag.

        Args:
            tag: Tag to filter by
            enabled_only: Only return enabled tools

        Returns:
            List of tool names with the tag
        """
        tools = []
        for name, meta in cls._metadata.items():
            if enabled_only and not meta.get("enabled", True):
                continue
            tags = meta.get("tags", [])
            if tag in tags:
                tools.append(name)
        return tools

    @classmethod
    def get_schemas(cls, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get OpenAI function calling schemas for specified tools.

        Args:
            tool_names: List of tool names to get schemas for. If None, returns all enabled tools.

        Returns:
            List of OpenAI function calling schema dictionaries
        """
        if tool_names is None:
            tool_names = cls.list_tools(enabled_only=True)

        schemas = []
        for tool_name in tool_names:
            try:
                tool_instance = cls.create(tool_name)
                schema = tool_instance.get_schema()
                schemas.append(schema)
            except Exception as e:
                cls._logger.warning(f"Failed to get schema for tool '{tool_name}': {e}")

        return schemas

    @classmethod
    def clear(cls):
        """Clear all registered tools. Useful for testing."""
        cls._tools.clear()
        cls._metadata.clear()
        cls._logger.debug("Cleared tool registry")


def register_tool(
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    enabled: bool = True,
    **metadata,
) -> Callable:
    """
    Decorator to register a tool class with the ToolRegistry.

    Usage:
        @register_tool(category="web", tags=["search", "api"])
        class WebSearchTool(BaseTool):
            ...

    Args:
        category: Tool category (e.g., "web", "file", "data")
        tags: List of tags for tool discovery
        enabled: Whether tool is enabled for use
        **metadata: Additional metadata to store

    Returns:
        Decorator function
    """

    def decorator(tool_class: Type[BaseTool]) -> Type[BaseTool]:
        ToolRegistry.register(
            tool_class=tool_class,
            category=category,
            tags=tags,
            enabled=enabled,
            **metadata,
        )
        return tool_class

    return decorator
