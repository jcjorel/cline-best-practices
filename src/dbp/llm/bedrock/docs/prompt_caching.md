# Prompt Caching in Amazon Bedrock

This document describes how to use the prompt caching feature with Amazon Bedrock models in the DBP library.

## Overview

Amazon Bedrock prompt caching optimizes token processing for large language models by caching repetitive inputs.
This can reduce costs by up to 90% and latency by up to 85% by avoiding reprocessing identical parts of prompts.

### Supported Models

The following Amazon Bedrock models support prompt caching:

- Claude 3.5 Haiku
- Claude 3.7 Sonnet
- Nova Micro
- Nova Lite
- Nova Pro

## Usage Guide

### 1. Check Model Support

First, check if your model supports prompt caching:

```python
from dbp.llm.bedrock.models.claude3 import ClaudeClient
from dbp.llm.bedrock.enhanced_base import ModelCapability

# Initialize model client
client = ClaudeClient("anthropic.claude-3-5-haiku-20241022-v1:0")
await client.initialize()

# Check if the model supports prompt caching
supports_caching = client.has_capability(ModelCapability.PROMPT_CACHING)
print(f"Model supports prompt caching: {supports_caching}")
```

### 2. Enable Prompt Caching

Enable prompt caching for the model:

```python
# Enable prompt caching
caching_enabled = client.enable_prompt_caching()
print(f"Prompt caching enabled: {caching_enabled}")

# Note: Returns False if model doesn't support prompt caching
```

### 3. Mark Cache Points

Mark cache points in your conversation for optimal caching:

```python
# Create messages with static content at the beginning
messages = [
    {"role": "system", "content": "You are a helpful assistant for AWS."},
    {"role": "user", "content": "What is Amazon Bedrock?"}
]

# Mark a cache point
result = client.mark_cache_point(messages)

# Use the marked messages in your API call
if result["cache_active"]:
    response = await client.stream_chat(result["messages"])
else:
    response = await client.stream_chat(messages)  # Use original messages
```

### 4. Best Practices for Prompt Caching

- **Place static content at the beginning** of your prompts for maximum cache hits
- **Mark cache points** for messages that will be reused frequently
- **Check if caching is enabled** before using cache-specific features
- **Use custom cache IDs** for more control over caching behavior

## API Reference

### `has_capability(ModelCapability.PROMPT_CACHING)`

Check if a model supports prompt caching.

**Returns:** Boolean indicating support status

### `enable_prompt_caching(enabled: bool = True)`

Enable or disable prompt caching for the current model.

**Parameters:**
- `enabled` - Boolean to enable/disable caching (default: True)

**Returns:** Boolean indicating if caching is now enabled

### `is_prompt_caching_enabled()`

Check if prompt caching is currently enabled and supported.

**Returns:** Boolean indicating current caching status

### `mark_cache_point(messages, cache_id = None)`

Mark a cache point in a conversation.

**Parameters:**
- `messages` - List of message objects to mark with cache point
- `cache_id` - Optional custom cache ID (generated if not provided)

**Returns:** Dictionary with:
- `cache_id` - The ID of the cache point
- `cache_active` - Whether caching is active
- `status` - "marked" if cache point was added, "ignored" if not
- `messages` - Modified messages with cache point metadata
- `timestamp` - When the cache point was created
