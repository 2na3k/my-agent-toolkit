# Router Agent

A scalable agent routing system that routes inputs to specialized agents based on metadata-driven patterns and keywords.

## Overview

The RouterAgent provides intelligent routing of inputs to specialized agents using a pluggable strategy system. The current implementation uses metadata-based routing (pattern and keyword matching), with support for future strategies like LLM-based intent detection.

## Architecture

```
RouterAgent (inherits BaseAgent)
    └── RoutingEngine
            ├── MetadataBasedStrategy (queries AgentFactory for agent metadata)
            └── LLMIntentStrategy (future: intelligent routing)
            └── RouteExecutor (agent lifecycle management)
```

### Key Components

1. **RouterAgent** - Main agent that orchestrates routing and execution
2. **RoutingEngine** - Manages routing strategies and determines which agent to use
3. **RouteExecutor** - Creates and executes the target agent
4. **MetadataBasedStrategy** - Routes based on regex patterns and keyword matching
5. **Data Models** - `RouteMatch` and `RouteResult` for routing decisions

## Usage

### Basic Usage

```python
from src.core import AgentFactory

# Create router (uses default settings)
router = AgentFactory.create("router")

# Route and execute
result = router.run("hello world")
print(result)  # Output: "hello"

# Get routing statistics
stats = router.get_routing_stats()
print(f"Routed to: {stats['last_route']['agent']}")
print(f"Confidence: {stats['last_route']['confidence']}")
```

### Custom Configuration

```python
# Create router with custom settings
router = AgentFactory.create(
    "router",
    default_agent="hello_agent",      # Fallback agent
    confidence_threshold=0.6          # Minimum confidence to accept match
)
```

## Adding New Agents

To add a new agent that the router can route to, simply use the enhanced `@register_agent` decorator:

```python
from src.core import BaseAgent, register_agent

@register_agent(
    "research_agent",
    patterns=[r"research", r"find\s+information", r"look\s+up"],
    keywords=["research", "investigate", "find", "search"],
    description="Performs deep research with web search and citations",
    priority=10  # Higher priority than hello_agent
)
class ResearchAgent(BaseAgent):
    def run(self, input_data, **kwargs):
        # Research implementation
        return self.perform_research(input_data)
```

The router will automatically discover and route to this agent based on the metadata you provide. No configuration files to maintain!

### Routing Metadata Parameters

- **patterns** - List of regex patterns to match (case-insensitive)
- **keywords** - List of keywords to match in the input
- **description** - Human-readable description of the agent
- **priority** - Higher priority agents are checked first (default: 0)
- **enabled** - Whether agent is available for routing (default: True)

## Routing Strategies

### MetadataBasedStrategy (Current)

Routes based on:
1. **Pattern Matching** - Regex patterns defined in agent metadata (confidence: 1.0)
2. **Keyword Matching** - Keywords present in input (confidence: proportional to match ratio)
3. **Priority** - Higher priority agents checked first

### Future Strategies

- **LLMIntentStrategy** - Use LLM to intelligently determine user intent and route accordingly
- **LangGraph Integration** - Multi-step workflows when needed
- **Hybrid Strategies** - Combine multiple strategies for better routing

## API Reference

### RouterAgent

```python
class RouterAgent(BaseAgent):
    def __init__(
        self,
        name: str = "RouterAgent",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config_path: Optional[str] = None,
        default_agent: str = "hello_agent",
        confidence_threshold: float = 0.5,
        **kwargs
    )

    def run(self, input_data: Any, **kwargs) -> Any:
        """Route input to appropriate agent and return result."""

    def route(self, input_data: Any, context: Optional[Dict] = None) -> RouteResult:
        """Determine which agent should handle the input."""

    def execute_route(self, route_result: RouteResult, input_data: Any, **kwargs) -> Any:
        """Execute the routed agent."""

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get statistics about routing decisions."""
```

### AgentFactory Metadata Methods

```python
# Get metadata for a specific agent
metadata = AgentFactory.get_metadata("hello_agent")

# Get all agent metadata
all_metadata = AgentFactory.get_all_metadata()

# Get only routable agents (enabled=True)
routable = AgentFactory.get_routable_agents()
```

## Examples

### Example 1: Routing to HelloAgent

```python
router = AgentFactory.create("router")

# All these will route to hello_agent
router.run("hello")           # Pattern match: r".*"
router.run("hi there")        # Pattern match
router.run("greet me")        # Keyword match: "greet"
```

### Example 2: Priority-based Routing

```python
@register_agent(
    "high_priority",
    patterns=[r"urgent"],
    priority=100
)
class UrgentAgent(BaseAgent):
    def run(self, input_data, **kwargs):
        return "Handling urgent request"

@register_agent(
    "low_priority",
    patterns=[r"urgent"],
    priority=1
)
class NormalAgent(BaseAgent):
    def run(self, input_data, **kwargs):
        return "Handling normal request"

# "urgent request" will route to UrgentAgent (higher priority)
router.run("urgent request")
```

### Example 3: Confidence Threshold

```python
# Only accept high-confidence matches
router = AgentFactory.create("router", confidence_threshold=0.8)

# Low confidence match will fall back to default agent
router.run("some random text")
```

## Testing

### Run Router Tests

```bash
# Run all router tests
pytest tests/test_router.py -v

# Run with coverage
pytest tests/test_router.py --cov=src/agents/router --cov-report=term-missing
```

### Run End-to-End Test

```bash
python test_router_e2e.py
```

## Design Decisions

1. **Metadata-Driven Routing** - Agents self-declare their routing rules via decorator, making the system self-documenting and maintainable

2. **Strategy Pattern** - Routing logic is pluggable, allowing easy addition of new routing strategies without modifying core code

3. **Lazy Agent Creation** - Agents are created only when needed via AgentFactory, reducing resource usage

4. **Infinite Loop Prevention** - Router is registered with `enabled=False` to prevent routing to itself

5. **Confidence-Based Fallback** - Routes below confidence threshold fall back to default agent, ensuring robustness

## Future Enhancements

1. **LLMIntentStrategy** - Use LLM to understand user intent for more intelligent routing
2. **Agent Caching** - Pool frequently used agents for better performance
3. **Metrics/Monitoring** - Track routing performance and accuracy
4. **Dynamic Route Reloading** - Hot-reload routing metadata without restart
5. **Multi-Agent Workflows** - Support for routing to multiple agents in sequence

## Files

- `agent.py` - RouterAgent implementation
- `engine.py` - RoutingEngine orchestration
- `executor.py` - RouteExecutor for agent lifecycle
- `models.py` - Data models (RouteMatch, RouteResult)
- `strategies/base.py` - RoutingStrategy interface
- `strategies/metadata.py` - MetadataBasedStrategy implementation
