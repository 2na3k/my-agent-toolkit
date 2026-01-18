# CLI Interface

A powerful command-line interface for the Agent Toolkit with two main modes: interactive chat and direct agent invocation.

## Quick Start

```bash
# Interactive chat mode
aa chat

# Direct agent invocation
aa invoke -a hello_agent -m "hello world"

# List available agents
aa agents

# Show help
aa --help
```

## Installation

After installing the package with `uv sync`, the `aa` command will be available:

```bash
uv sync
aa --help
```

## Commands

### Interactive Chat Mode

Start an interactive REPL-style chat session:

```bash
aa chat
```

**Options:**
- `--provider`, `-p` - AI provider (claude, gemini, openai)
- `--model`, `-m` - Specific model to use
- `--no-router` - Disable router (pure LLM mode)
- `--verbose`, `-v` - Enable verbose logging

**Example:**
```bash
# Chat with default provider
aa chat

# Chat with specific provider and model
aa chat --provider gemini --model gemini-2.0-flash-exp

# Chat without router (pure LLM)
aa chat --no-router
```

#### Special Commands

While in chat mode, use these commands:

- `/help`, `/h` - Show available commands
- `/exit`, `/quit`, `/q` - Exit chat
- `/reset`, `/clear` - Reset conversation history
- `/context`, `/c` - Show conversation context
- `/agents` - List available agents
- `/history` - Show conversation history

**Example Session:**
```bash
$ aa chat

╭────────────────────────────────────────╮
│  Agent Toolkit - Interactive Chat     │
│  Provider: claude | Model: sonnet 4.5 │
│  Router: enabled                      │
╰────────────────────────────────────────╯

You: hello
Assistant: hello

You: tell me about Python
Assistant: Python is a versatile programming language...

You: /context
┌─────────────────────────────┐
│  Conversation Context       │
├─────────────────────────────┤
│  History: 2 exchanges       │
│  Provider: claude           │
│  Router enabled: True       │
└─────────────────────────────┘

You: /exit
Goodbye! 👋
```

### Direct Agent Invocation

Invoke a specific agent with a one-shot command:

```bash
aa invoke -a <agent> -m "message"
```

**Options:**
- `--agent`, `-a` - Agent to invoke (required)
- `--message`, `-m` - Message to send (required)
- `--file`, `-f` - File(s) to attach (can be used multiple times)
- `--provider`, `-p` - AI provider
- `--model` - Model to use
- `--output`, `-o` - Save output to file
- `--format` - Output format (text, json)
- `--verbose`, `-v` - Enable verbose logging

**Examples:**

```bash
# Simple invocation
aa invoke -a hello_agent -m "hello"

# With file attachment
aa invoke -a convo -m "summarize this" -f document.pdf

# Multiple files
aa invoke -a convo -m "compare these" -f doc1.pdf -f doc2.pdf

# Custom provider and model
aa invoke -a convo -m "hello" --provider gemini --model gemini-2.0-flash-exp

# Save output to file
aa invoke -a convo -m "hello" --output result.txt

# JSON output format
aa invoke -a convo -m "hello" --format json

# Verbose mode
aa invoke -a convo -m "hello" --verbose
```

### List Agents

List all available agents:

```bash
aa agents
```

**Output:**
```
Available Agents:

○ convo
  Main conversation agent that orchestrates chat workflow

● hello_agent
  A simple agent that always returns 'hello'
  Patterns: ^hello\b, ^hi\b, ^hey\b...

○ router
  Routes inputs to specialized agents based on metadata
```

- ● Green dot = routable agent (can be auto-selected by router)
- ○ Gray dot = non-routable agent (must be explicitly invoked)

### Version

Show version information:

```bash
aa version
```

## File Attachments

The CLI supports various file types for the `invoke` command:

**Text Files:**
- `.txt`, `.md`, `.py`, `.js`, `.json`, `.yaml`, `.csv`
- Read as UTF-8 text

**Images:**
- `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`
- Base64 encoded for multimodal input

**PDFs:**
- `.pdf`
- Base64 encoded

**File Size Limit:** 10MB per file

**Example:**
```bash
# Attach a text file
aa invoke -a convo -m "analyze this code" -f script.py

# Attach an image
aa invoke -a convo -m "describe this image" -f photo.jpg

# Attach a PDF
aa invoke -a convo -m "summarize this document" -f report.pdf
```

## Output Formats

### Text Format (default)

Plain text output with markdown rendering:

```bash
aa invoke -a convo -m "explain Python"
```

### JSON Format

Structured JSON output:

```bash
aa invoke -a convo -m "hello" --format json
```

**Output:**
```json
{
  "result": "I'm Claude, an AI assistant..."
}
```

## Configuration

### Environment Variables

Set AI provider API keys:

```bash
export ANTHROPIC_API_KEY="your-key"
export GEMINI_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

Or use a `.env` file:

```env
ANTHROPIC_API_KEY=your-key
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
```

### Provider Selection

Default provider is set in `config.yaml`. Override with `--provider`:

```bash
aa chat --provider claude
aa chat --provider gemini
aa chat --provider openai
```

### Model Selection

Specify a model with `--model`:

```bash
aa chat --model gpt-4o
aa invoke -a convo -m "hello" --model gemini-2.0-flash-exp
```

## Error Handling

The CLI provides user-friendly error messages:

```bash
$ aa invoke -a unknown_agent -m "test"
Error: Agent 'unknown_agent' not found. Available agents: hello_agent, convo, router
```

Enable verbose mode for detailed error information:

```bash
aa invoke -a convo -m "test" --verbose
```

## Architecture

```
CLI Entry Point (aa)
    ↓
┌─────────────────┬─────────────────┐
│  Chat Mode      │  Invoke Mode    │
│  (Interactive)  │  (One-shot)     │
├─────────────────┼─────────────────┤
│ ChatInterface   │ AgentInvoker    │
│ - REPL loop     │ - Parse args    │
│ - Commands      │ - Load files    │
│ - Display       │ - Execute agent │
└─────────────────┴─────────────────┘
    ↓                    ↓
┌────────────────────────────────────┐
│       AgentFactory                 │
│  (ConvoAgent, RouterAgent, etc.)   │
└────────────────────────────────────┘
```

## Files

- `main.py` - Entry point and command definitions
- `chat_interface.py` - Interactive chat REPL
- `chat_commands.py` - Special chat commands
- `agent_invoker.py` - Direct agent invocation
- `file_handler.py` - File attachment handling
- `output_formatter.py` - Output formatting and display

## Testing

Run CLI tests:

```bash
python test_cli_e2e.py
```

## Tips & Tricks

1. **Quick Chat:** Use `aa chat` for quick conversations
2. **Agent Discovery:** Use `aa agents` to see what's available
3. **Command Reference:** Use `/help` in chat mode for commands
4. **File Processing:** Attach files with `-f` for document analysis
5. **JSON Output:** Use `--format json` for structured data
6. **Verbose Mode:** Add `--verbose` for debugging

## Troubleshooting

### "API key not found" Error

Make sure your `.env` file has the required API keys:

```bash
# Create .env file
echo "ANTHROPIC_API_KEY=your-key" > .env
```

### "Agent not found" Error

List available agents:

```bash
aa agents
```

### Command Not Found

Make sure the package is installed:

```bash
uv sync
```

## Future Enhancements

- [ ] Multi-line input support
- [ ] Chat history persistence
- [ ] Streaming responses
- [ ] Autocomplete for commands
- [ ] Session management
- [ ] Clipboard integration
- [ ] Shell autocomplete (bash, zsh, fish)
