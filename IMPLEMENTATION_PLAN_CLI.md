# CLI Implementation Plan

## Overview

Build a command-line interface (CLI) for the agent toolkit with two main modes:
1. **Interactive Chat Mode** - `aa chat` for conversational interactions
2. **Direct Agent Mode** - `aa -a <agent> -m "message" -f <file>` for one-shot agent invocations

## Requirements

### Functional Requirements

1. **Interactive Chat Mode (`aa chat`)**
   - Start an interactive REPL-style chat session
   - Use ConvoAgent as the backend
   - Maintain conversation history within session
   - Support special commands (e.g., `/help`, `/reset`, `/exit`, `/context`)
   - Pretty-print responses with syntax highlighting
   - Show typing indicators for better UX

2. **Direct Agent Mode (`aa -a <agent> -m "message" -f <file>`)**
   - Invoke specific agent directly
   - Support message input via `-m` flag
   - Support file attachments via `-f` flag
   - Handle multimodal inputs (text + files)
   - Output result and exit

3. **General Features**
   - Provider selection (Claude, Gemini, OpenAI)
   - Model selection
   - Configuration via command-line flags or config file
   - Error handling with user-friendly messages
   - Logging (optional verbose mode)

### Non-Functional Requirements

1. **User Experience**
   - Fast startup time
   - Clear error messages
   - Helpful usage information
   - Progressive disclosure (don't overwhelm with options)

2. **Extensibility**
   - Easy to add new commands
   - Plugin-like architecture for chat commands
   - Support for future features (streaming, tool use, etc.)

## Architecture

```
┌─────────────────────────────────────────────┐
│              CLI Entry Point                │
│           (aa command / main.py)            │
└─────────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────────┐
│   Chat Mode     │    │  Direct Agent Mode  │
│   (interactive) │    │   (one-shot)        │
└─────────────────┘    └─────────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────────┐
│  ChatInterface  │    │   AgentInvoker      │
│  - REPL loop    │    │  - Parse args       │
│  - Commands     │    │  - Load file        │
│  - History      │    │  - Execute agent    │
│  - Display      │    │  - Format output    │
└─────────────────┘    └─────────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │    AgentFactory       │
         │   (ConvoAgent, etc.)  │
         └───────────────────────┘
```

## Implementation Phases

### Phase 1: Core CLI Structure

**Goal:** Set up basic CLI framework with argument parsing

**Files to Create:**
- `src/cli/main.py` - Entry point and argument parser
- `src/cli/config.py` - CLI configuration management
- `src/cli/__init__.py` - Package initialization

**Tasks:**
1. Set up Click or Typer for CLI framework (recommend Typer for type safety)
2. Define main command group
3. Implement basic argument parsing for both modes
4. Add help text and usage documentation
5. Create CLI configuration loader (extends main config.yaml)

**Deliverables:**
- `aa --help` shows usage information
- `aa chat --help` shows chat mode help
- `aa -a hello_agent -m "test"` parses arguments correctly (no execution yet)

### Phase 2: Direct Agent Mode

**Goal:** Implement one-shot agent invocation

**Files to Create:**
- `src/cli/agent_invoker.py` - Direct agent invocation logic
- `src/cli/file_handler.py` - File attachment handling
- `src/cli/output_formatter.py` - Output formatting utilities

**Tasks:**
1. Implement AgentInvoker class
   - Parse command-line arguments
   - Validate agent exists
   - Handle message input
   - Handle file attachments (read, encode, prepare for multimodal)
   - Execute agent with AgentFactory
   - Format and display output

2. File handling
   - Support common file types (txt, md, pdf, images, etc.)
   - Read file content
   - Encode for multimodal input (images as base64, etc.)
   - Validate file size limits

3. Output formatting
   - Pretty-print results
   - Handle different output types (text, JSON, etc.)
   - Color-coding for better readability
   - Error formatting

**Example Usage:**
```bash
# Simple message
aa -a hello_agent -m "hello"

# With file attachment
aa -a convo -m "what's in this file?" -f document.pdf

# Custom provider/model
aa -a convo -m "hello" --provider gemini --model gemini-2.0-flash-exp
```

**Deliverables:**
- Working one-shot agent invocation
- File attachment support
- Formatted output display

### Phase 3: Interactive Chat Mode

**Goal:** Implement REPL-style chat interface

**Files to Create:**
- `src/cli/chat_interface.py` - Interactive chat REPL
- `src/cli/chat_commands.py` - Special chat commands handler
- `src/cli/display.py` - Rich display utilities (colors, formatting, etc.)

**Tasks:**
1. Implement ChatInterface class
   - REPL loop with prompt
   - User input handling
   - Message history display
   - Graceful exit handling
   - Ctrl+C handling

2. Special commands
   - `/help` - Show available commands
   - `/reset` - Reset conversation
   - `/context` - Show conversation context
   - `/exit` or `/quit` - Exit chat
   - `/provider <name>` - Switch provider
   - `/model <name>` - Switch model
   - `/agents` - List available agents
   - `/history` - Show conversation history

3. Display enhancements
   - Use Rich library for beautiful terminal output
   - Syntax highlighting for code blocks
   - Markdown rendering
   - Typing indicators (optional)
   - Timestamps
   - Token usage display (optional)

**Example Session:**
```bash
$ aa chat

╭────────────────────────────────────────╮
│  Agent Toolkit - Interactive Chat     │
│  Provider: claude | Model: sonnet 4.5 │
│  Type /help for commands, /exit to quit│
╰────────────────────────────────────────╯

You: hello
Assistant: hello

You: who are you?
Assistant: I'm Claude, an AI assistant...

You: /context
┌─────────────────────────────┐
│  Conversation Context       │
├─────────────────────────────┤
│  History: 2 exchanges       │
│  Provider: claude           │
│  Model: sonnet 4.5          │
│  Router enabled: True       │
│  Last route: None (LLM)     │
└─────────────────────────────┘

You: /exit
Goodbye! 👋
```

**Deliverables:**
- Working interactive chat REPL
- Special commands implemented
- Rich terminal display
- Session persistence (optional)

### Phase 4: Configuration & Convenience

**Goal:** Add configuration management and convenience features

**Files to Create:**
- `src/cli/cli_config.yaml` - CLI-specific configuration (optional)
- `setup.py` or `pyproject.toml` update - Add `aa` command entry point

**Tasks:**
1. Entry point setup
   - Add `aa` command to installed scripts
   - Create shell script for development
   - Add to PATH

2. Configuration management
   - CLI-specific config file
   - Environment variable support
   - Config precedence: CLI flags > env vars > config file > defaults

3. Convenience features
   - Default provider/model from config
   - Save chat history to file (optional)
   - Load previous session (optional)
   - Alias support for common agents

**Deliverables:**
- `aa` command available globally after install
- Configuration system working
- Development script for testing

### Phase 5: Testing & Documentation

**Goal:** Ensure reliability and usability

**Files to Create:**
- `tests/test_cli.py` - CLI tests
- `tests/test_chat_interface.py` - Chat interface tests
- `tests/test_agent_invoker.py` - Agent invoker tests
- `docs/CLI_USER_GUIDE.md` - User documentation

**Tasks:**
1. Unit tests
   - Test argument parsing
   - Test agent invocation logic
   - Test file handling
   - Test command parsing
   - Mock AgentFactory for tests

2. Integration tests
   - End-to-end chat session (mocked)
   - End-to-end agent invocation (mocked)
   - Error handling scenarios

3. Documentation
   - User guide with examples
   - Command reference
   - Configuration guide
   - Troubleshooting section

**Deliverables:**
- Comprehensive test coverage
- User documentation
- Developer documentation

## Technology Stack

### Core CLI Framework
- **Typer** (recommended) or Click - Type-safe CLI framework
  - Pros: Type hints, automatic help, better DX
  - Cons: Slightly more opinionated

### Display & Formatting
- **Rich** - Beautiful terminal output
  - Markdown rendering
  - Syntax highlighting
  - Tables, panels, progress bars
  - Color support

### Optional Libraries
- **prompt_toolkit** - Advanced input handling (autocomplete, history)
- **pyperclip** - Clipboard support for copy/paste
- **python-dotenv** - Environment variable loading

## File Structure

```
src/cli/
├── __init__.py
├── main.py                # Entry point, argument parsing
├── chat_interface.py      # Interactive chat REPL
├── chat_commands.py       # Special chat commands (/help, /reset, etc.)
├── agent_invoker.py       # Direct agent invocation
├── file_handler.py        # File attachment handling
├── output_formatter.py    # Output formatting utilities
├── display.py            # Rich display utilities
├── config.py             # CLI configuration
└── README.md             # Updated with implementation details

tests/
├── test_cli.py
├── test_chat_interface.py
├── test_agent_invoker.py
└── test_file_handler.py
```

## Implementation Priority

### Must-Have (MVP)
1. ✅ Basic CLI framework with argument parsing
2. ✅ Direct agent mode (`aa -a <agent> -m "message"`)
3. ✅ Interactive chat mode (`aa chat`)
4. ✅ Basic output formatting
5. ✅ Error handling

### Should-Have (v1.0)
1. File attachment support (`-f` flag)
2. Special chat commands (`/help`, `/reset`, `/exit`)
3. Rich terminal display
4. Configuration management
5. Provider/model selection

### Nice-to-Have (v1.1+)
1. Chat history persistence
2. Autocomplete for commands
3. Streaming responses
4. Clipboard integration
5. Session management
6. Multi-line input support

## Key Design Decisions

### 1. CLI Framework: Typer vs Click
**Decision:** Use Typer
**Rationale:**
- Type-safe with Python type hints
- Automatic help generation
- Better developer experience
- Modern and actively maintained
- Easy to add subcommands

### 2. Display Library: Rich
**Decision:** Use Rich for terminal output
**Rationale:**
- Beautiful, modern terminal UI
- Markdown and syntax highlighting built-in
- Progress indicators
- Tables and panels
- Wide adoption, good documentation

### 3. Chat History
**Decision:** In-memory for MVP, optional file persistence
**Rationale:**
- Simpler implementation
- Faster for interactive sessions
- Can add persistence later as feature
- Avoid complexity of history management initially

### 4. File Handling
**Decision:** Support common formats, validate size
**Rationale:**
- Text files: direct string content
- Images: base64 encode for multimodal
- PDFs: extract text or pass raw (model-dependent)
- Size limit: 10MB default (configurable)

### 5. Error Handling
**Decision:** User-friendly messages, optional verbose mode
**Rationale:**
- Don't show stack traces to end users by default
- Add `--verbose` flag for debugging
- Log errors to file in debug mode

## Example Commands Specification

### Interactive Chat Mode

```bash
# Start chat with default provider/model
aa chat

# Start chat with specific provider
aa chat --provider gemini

# Start chat with specific model
aa chat --model gpt-4o

# Start chat with verbose logging
aa chat --verbose

# Start chat and load previous session (future)
aa chat --session my-session
```

### Direct Agent Mode

```bash
# Invoke specific agent
aa -a hello_agent -m "hello"
aa --agent hello_agent --message "hello"

# With file attachment
aa -a convo -m "summarize this" -f document.pdf

# Multiple files (future)
aa -a convo -m "compare these" -f doc1.pdf -f doc2.pdf

# Custom provider/model
aa -a convo -m "hello" --provider gemini --model gemini-2.0-flash-exp

# Output to file
aa -a convo -m "hello" --output result.txt

# JSON output format
aa -a convo -m "hello" --format json

# Verbose mode
aa -a convo -m "hello" --verbose
```

### Utility Commands

```bash
# List available agents
aa --list-agents
aa agents

# Show configuration
aa config

# Show version
aa --version

# Show help
aa --help
aa -h
```

## Success Criteria

### MVP Success
- [ ] User can run `aa chat` and have conversation with ConvoAgent
- [ ] User can run `aa -a hello_agent -m "hello"` and get response
- [ ] Help text is clear and useful
- [ ] Errors are handled gracefully with clear messages
- [ ] CLI is installable and `aa` command works globally

### v1.0 Success
- [ ] File attachments work for common formats
- [ ] Chat commands (`/help`, `/reset`, etc.) work correctly
- [ ] Display is beautiful and readable (Rich formatting)
- [ ] Configuration management works (flags, env vars, config file)
- [ ] Provider/model switching works
- [ ] Comprehensive tests with >80% coverage
- [ ] User documentation is complete

## Risks & Mitigations

### Risk 1: Multimodal File Handling Complexity
**Mitigation:**
- Start with text files only
- Add image support second
- Research model-specific requirements early
- Have fallback for unsupported formats

### Risk 2: Interactive Mode UX Complexity
**Mitigation:**
- Start simple (basic prompt)
- Add Rich features incrementally
- User testing with real users
- Gather feedback early and often

### Risk 3: Configuration Complexity
**Mitigation:**
- Use sensible defaults
- Keep config simple initially
- Document all options clearly
- Provide configuration templates

### Risk 4: Cross-Platform Compatibility
**Mitigation:**
- Test on macOS, Linux, Windows
- Use cross-platform libraries (Rich works everywhere)
- Handle terminal encoding differences
- Provide fallbacks for limited terminals

## Timeline Estimate

### Phase 1: Core CLI Structure (2-3 hours)
- Set up Typer framework
- Basic argument parsing
- Configuration loading

### Phase 2: Direct Agent Mode (3-4 hours)
- Agent invocation logic
- Basic file handling
- Output formatting

### Phase 3: Interactive Chat Mode (4-6 hours)
- REPL implementation
- Special commands
- Rich display integration

### Phase 4: Configuration & Convenience (2-3 hours)
- Entry point setup
- Config management
- Convenience features

### Phase 5: Testing & Documentation (3-4 hours)
- Write tests
- Documentation
- Polish and bug fixes

**Total Estimate: 14-20 hours**

## Next Steps

1. **Review and Approve Plan** - Get stakeholder approval
2. **Set Up Environment** - Install Typer, Rich
3. **Start Phase 1** - Basic CLI framework
4. **Iterate** - Build, test, refine each phase
5. **Launch MVP** - Get it in users' hands
6. **Gather Feedback** - Improve based on usage
7. **Build v1.0** - Add nice-to-have features

## Open Questions

1. Should we support stdin input? (`echo "hello" | aa -a convo`)
2. Should we have a daemon mode for faster subsequent calls?
3. Should chat history be saved by default or opt-in?
4. What's the desired behavior for Ctrl+C during LLM generation?
5. Should we support piping output? (`aa -a convo -m "hello" | jq`)
6. Do we need shell autocomplete support? (bash, zsh, fish)

## References

- Typer Documentation: https://typer.tiangolo.com/
- Rich Documentation: https://rich.readthedocs.io/
- Click Documentation: https://click.palletsprojects.com/
- prompt_toolkit: https://python-prompt-toolkit.readthedocs.io/
