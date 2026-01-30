# Custom Provider Integration Guide

This guide explains how to integrate custom model providers (Ollama, LlamaCpp, LM Studio, etc.) with the agent toolkit and use tools with them.

## Overview

The toolkit uses the OpenAI SDK as a universal interface, which means **any provider with an OpenAI-compatible API can be integrated**. This includes:

- **Ollama** - Local LLM runner (most popular)
- **LlamaCpp** - C++ implementation with Python bindings
- **LM Studio** - GUI-based local LLM runner
- **vLLM** - High-performance inference server
- **Text Generation WebUI** - Gradio-based interface
- **Jan** - Desktop app for local LLMs
- **Any custom OpenAI-compatible endpoint**

## Quick Start

### 1. Add Provider Configuration

Edit `config.yaml` and add your custom provider:

```yaml
providers:
  # ... existing providers ...

  ollama:
    base_url: "http://localhost:11434/v1/"
    default_model: "qwen2.5:latest"
    models:
      - "qwen2.5:latest"
      - "llama3.2:latest"
      - "mistral:latest"
    timeout: 120
    max_retries: 2
    requires_api_key: false          # Local provider, no API key needed
    default_api_key: "not-needed"    # Dummy key for OpenAI SDK compatibility
```

### 2. Use with CLI

```bash
# Interactive chat with custom provider
aa chat --provider ollama --model qwen2.5:latest

# Invoke agent with custom provider
aa invoke -a convo -m "list files in /tmp" --provider ollama
```

### 3. Use in Code

```python
import src.tools
import src.agents
from src.core import AgentFactory

# Create agent with custom provider
agent = AgentFactory.create(
    "convo",
    provider="ollama",
    model="qwen2.5:latest",
    enable_tools=True,
    use_router=False
)

# Chat with tool support
result = agent.run("list the files in /tmp")
print(result)
```

## Detailed Configuration

### Provider Configuration Options

```yaml
custom_provider:
  base_url: "http://localhost:PORT/v1/"    # OpenAI-compatible endpoint (required)
  default_model: "model-name"              # Default model to use (required)
  models:                                  # List of available models (optional)
    - "model-name"
    - "another-model"
  timeout: 120                             # Request timeout in seconds (optional, default: 60)
  max_retries: 2                           # Number of retries on failure (optional, default: 3)
  requires_api_key: false                  # Whether API key is required (optional, default: true)
  default_api_key: "not-needed"            # Dummy key for local providers (optional)
```

### API Key Handling

The toolkit supports three ways to handle API keys:

#### 1. Required API Key (Cloud Providers)

```yaml
my_cloud_provider:
  base_url: "https://api.example.com/v1/"
  default_model: "model-name"
  requires_api_key: true  # or omit (defaults to true)
```

Set environment variable:
```bash
export MY_CLOUD_PROVIDER_API_KEY="your-api-key"
```

#### 2. Local Provider (No API Key)

```yaml
ollama:
  base_url: "http://localhost:11434/v1/"
  default_model: "qwen2.5:latest"
  requires_api_key: false
  default_api_key: "not-needed"
```

No environment variable needed.

#### 3. Custom Environment Variable

```yaml
my_provider:
  base_url: "https://api.example.com/v1/"
  default_model: "model-name"
```

The toolkit will automatically look for `MY_PROVIDER_API_KEY` in environment variables.

## Popular Providers Setup

### Ollama

1. **Install Ollama**: https://ollama.ai/
2. **Start Ollama server**: `ollama serve` (usually starts automatically)
3. **Pull a model**: `ollama pull qwen2.5:latest`
4. **Configuration** (already in `config.yaml`):

```yaml
ollama:
  base_url: "http://localhost:11434/v1/"
  default_model: "qwen2.5:latest"
  models:
    - "qwen2.5:latest"
    - "llama3.2:latest"
    - "mistral:latest"
    - "phi3:latest"
  timeout: 120
  max_retries: 2
  requires_api_key: false
  default_api_key: "not-needed"
```

5. **Test**:
```bash
aa chat --provider ollama --model qwen2.5:latest
```

**Important**: For tool calling, use models that support function calling:
- ✅ `qwen2.5:latest` - Full function calling support
- ✅ `llama3.2:latest` - Supports function calling
- ✅ `mistral:latest` - Good function calling support
- ⚠️  Older models may not support function calling

### LlamaCpp Server

1. **Install llama-cpp-python with server**:
```bash
pip install 'llama-cpp-python[server]'
```

2. **Start server**:
```bash
python -m llama_cpp.server \
  --model /path/to/model.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --n_ctx 4096
```

3. **Configuration** (already in `config.yaml`):

```yaml
llamacpp:
  base_url: "http://localhost:8080/v1/"
  default_model: "local-model"
  timeout: 120
  max_retries: 2
  requires_api_key: false
  default_api_key: "not-needed"
```

4. **Test**:
```bash
aa chat --provider llamacpp
```

### LM Studio

1. **Download LM Studio**: https://lmstudio.ai/
2. **Load a model** in LM Studio
3. **Start Local Server** (in LM Studio):
   - Click "Local Server" tab
   - Click "Start Server"
   - Default port: 1234

4. **Configuration** (already in `config.yaml`):

```yaml
lmstudio:
  base_url: "http://localhost:1234/v1/"
  default_model: "local-model"
  timeout: 120
  max_retries: 2
  requires_api_key: false
  default_api_key: "not-needed"
```

5. **Test**:
```bash
aa chat --provider lmstudio
```

### vLLM

1. **Install vLLM**:
```bash
pip install vllm
```

2. **Start server**:
```bash
python -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --port 8000
```

3. **Add to config.yaml**:

```yaml
vllm:
  base_url: "http://localhost:8000/v1/"
  default_model: "mistralai/Mistral-7B-Instruct-v0.2"
  timeout: 120
  max_retries: 2
  requires_api_key: false
  default_api_key: "not-needed"
```

## Tool Support with Custom Providers

### Function Calling Requirements

For tools to work, the provider must support **OpenAI function calling format**:

```json
{
  "type": "function",
  "function": {
    "name": "bash",
    "description": "Execute bash commands...",
    "parameters": {
      "type": "object",
      "properties": {
        "command": {"type": "string", "description": "..."}
      },
      "required": ["command"]
    }
  }
}
```

### Compatibility Matrix

| Provider | Function Calling | Notes |
|----------|------------------|-------|
| Ollama | ✅ Yes (with compatible models) | Use qwen2.5, llama3.2, mistral |
| LlamaCpp | ⚠️  Depends on server config | Enable `--chat-format functionary` |
| LM Studio | ✅ Yes (with compatible models) | Check model card |
| vLLM | ✅ Yes | Built-in support |
| Text Gen WebUI | ⚠️  Experimental | Enable OpenAI extension |

### Testing Tool Support

Test if tool calling works with your provider:

```bash
# Start chat
aa chat --provider ollama --model qwen2.5:latest

# Try a tool-requiring command
> run the command: ls -la

# If tools work, you'll see:
# - LLM requesting tool call
# - Tool execution
# - LLM processing results
```

### Enabling Tools

Tools are **enabled by default** in ConvoAgent with these safe tools:
- `file_read` - Read files
- `bash` - Execute commands
- `file_list` - List directories
- `grep` - Search in files

To customize:

```python
agent = AgentFactory.create(
    "convo",
    provider="ollama",
    enable_tools=True,
    tools=["bash", "file_read", "file_write"]  # Specify tools
)
```

To disable:

```python
agent = AgentFactory.create(
    "convo",
    provider="ollama",
    enable_tools=False  # Pure LLM mode
)
```

## Troubleshooting

### Connection Refused

```
Error: Connection refused to localhost:11434
```

**Solution**: Ensure the provider's server is running:
- Ollama: `ollama serve` or check if service is running
- LlamaCpp: Start the server manually
- LM Studio: Click "Start Server" in the app

### API Key Error (Local Provider)

```
Error: API key not found
```

**Solution**: Add to your provider config:
```yaml
requires_api_key: false
default_api_key: "not-needed"
```

### Tool Calling Not Working

```
LLM returns plain text instead of using tools
```

**Solutions**:
1. **Check model compatibility**: Use models that support function calling
2. **Enable function calling in server**:
   - LlamaCpp: `--chat-format functionary`
   - Check provider docs for function calling support
3. **Test with a cloud provider first** to verify the tool system works
4. **Check logs**: Look for tool schema generation in logs

### Slow Response Times

```
Requests timing out or very slow
```

**Solutions**:
1. **Increase timeout** in config:
   ```yaml
   timeout: 300  # 5 minutes
   ```
2. **Use smaller models**: qwen2.5:3b instead of qwen2.5:7b
3. **Check hardware**: Ensure sufficient RAM/GPU
4. **Use quantized models**: GGUF Q4 or Q5 quantization

## Advanced: Adding Custom Provider

### Step 1: Test OpenAI Compatibility

Verify your provider has OpenAI-compatible endpoints:

```bash
curl http://localhost:PORT/v1/models
```

Should return:
```json
{
  "data": [
    {"id": "model-name", "object": "model"},
    ...
  ]
}
```

### Step 2: Add to Config

```yaml
my_custom_provider:
  base_url: "http://localhost:PORT/v1/"
  default_model: "model-name"
  models:
    - "model-name"
  timeout: 120
  requires_api_key: false  # or true if needed
  default_api_key: "not-needed"  # if no key needed
```

### Step 3: Test Connection

```python
from src.core import ClientFactory

factory = ClientFactory()
client = factory.create_client("my_custom_provider")

print(f"Provider: {client.current_provider}")
print(f"Base URL: {client.base_url}")
print(f"Model: {client.get_default_model()}")
```

### Step 4: Test Tool Calling

```python
import src.tools
import src.agents
from src.core import AgentFactory

agent = AgentFactory.create(
    "convo",
    provider="my_custom_provider",
    enable_tools=True,
    use_router=False
)

# Test with a simple command
result = agent.run("run the command: echo 'Hello from tools!'")
print(result)
```

## Best Practices

1. **Start with simple tasks**: Test basic chat before enabling tools
2. **Use compatible models**: Check model documentation for function calling support
3. **Monitor resource usage**: Local models can be resource-intensive
4. **Set appropriate timeouts**: Local inference can be slower than cloud APIs
5. **Test incrementally**: Test connection → basic chat → tool calling
6. **Check logs**: Enable verbose logging to debug issues
7. **Keep models updated**: Newer models have better function calling support

## Examples

### Example 1: Code Analysis with Ollama

```bash
aa chat --provider ollama --model qwen2.5:latest
> read the file src/core/agent.py and explain the BaseAgent class
```

### Example 2: File Operations with LM Studio

```bash
aa invoke -a convo -m "create a file called test.txt with 'Hello World'" --provider lmstudio
```

### Example 3: System Automation with LlamaCpp

```python
import src.tools, src.agents
from src.core import AgentFactory

agent = AgentFactory.create("convo", provider="llamacpp", enable_tools=True)

# Automated system check
tasks = [
    "check disk usage with: df -h",
    "list running processes with: ps aux | head -10",
    "check system uptime"
]

for task in tasks:
    result = agent.run(task)
    print(f"Task: {task}")
    print(f"Result: {result}\n")
```

## Resources

- **Ollama**: https://ollama.ai/
- **LlamaCpp**: https://github.com/ggerganov/llama.cpp
- **LM Studio**: https://lmstudio.ai/
- **vLLM**: https://github.com/vllm-project/vllm
- **Function Calling Guide**: https://platform.openai.com/docs/guides/function-calling

## Support

For issues with custom providers:
1. Check provider's documentation for OpenAI compatibility
2. Verify the provider's server is running
3. Test with `curl` to ensure API is accessible
4. Check toolkit logs for detailed error messages
5. Open an issue on GitHub with provider details and error logs
