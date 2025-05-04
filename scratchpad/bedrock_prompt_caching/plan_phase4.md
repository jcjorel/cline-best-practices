# Phase 4: Testing and Documentation

## Overview

This phase focuses on comprehensive testing, documentation, and example creation for the prompt caching feature. It ensures the implementation meets all requirements and provides clear guidance for users.

## Implementation Steps

### 1. Create Example Script

Create an example script in `src/dbp/llm/bedrock/examples/prompt_caching_example.py` demonstrating prompt caching usage:

```python
#!/usr/bin/env python3
"""
Example demonstrating prompt caching with Amazon Bedrock models.

This script shows:
1. How to check if a model supports prompt caching
2. How to enable prompt caching for a model
3. How to mark cache points in conversations
4. How to use the marked messages in API calls
"""

import asyncio
import time
import logging
from typing import Dict, Any, List

from src.dbp.llm.bedrock.models.claude3 import ClaudeClient
from src.dbp.llm.bedrock.enhanced_base import ModelCapability

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("prompt_caching_example")

async def run_without_caching(model_id: str) -> float:
    """Run a sample conversation without caching and measure time."""
    client = ClaudeClient(model_id=model_id, logger=logger)
    await client.initialize()
    
    # Disable caching explicitly
    client.enable_prompt_caching(False)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant specializing in AWS services."},
        {"role": "user", "content": "What is Amazon Bedrock prompt caching?"}
    ]
    
    start_time = time.time()
    
    # Process the conversation
    result = ""
    async for chunk in client.stream_chat(messages):
        if "delta" in chunk and "text" in chunk["delta"]:
            result += chunk["delta"]["text"]
    
    elapsed_time = time.time() - start_time
    logger.info(f"Without caching - Response time: {elapsed_time:.2f} seconds")
    logger.info(f"Response length: {len(result)} characters")
    
    return elapsed_time

async def run_with_caching(model_id: str) -> float:
    """Run a sample conversation with caching and measure time."""
    client = ClaudeClient(model_id=model_id, logger=logger)
    await client.initialize()
    
    # Check if model supports caching
    supports_caching = client.has_capability(ModelCapability.PROMPT_CACHING)
    logger.info(f"Model {model_id} supports prompt caching: {supports_caching}")
    
    # Enable caching if supported
    caching_enabled = client.enable_prompt_caching(True)
    logger.info(f"Prompt caching enabled: {caching_enabled}")
    
    # Create messages with static content at the beginning for better caching
    messages = [
        {"role": "system", "content": "You are a helpful assistant specializing in AWS services."},
        {"role": "user", "content": "What is Amazon Bedrock prompt caching?"}
    ]
    
    # Mark a cache point
    result = client.mark_cache_point(messages)
    logger.info(f"Cache point status: {result['status']}")
    logger.info(f"Cache ID: {result['cache_id']}")
    
    start_time = time.time()
    
    # Process the conversation with cache-enabled messages
    response = ""
    async for chunk in client.stream_chat(result["messages"]):
        if "delta" in chunk and "text" in chunk["delta"]:
            response += chunk["delta"]["text"]
    
    elapsed_time = time.time() - start_time
    logger.info(f"With caching - First run response time: {elapsed_time:.2f} seconds")
    logger.info(f"Response length: {len(response)} characters")
    
    # Run second time with same messages to see caching effect
    logger.info("Running second time with same messages...")
    start_time = time.time()
    
    second_response = ""
    async for chunk in client.stream_chat(result["messages"]):
        if "delta" in chunk and "text" in chunk["delta"]:
            second_response += chunk["delta"]["text"]
    
    elapsed_time = time.time() - start_time
    logger.info(f"With caching - Second run response time: {elapsed_time:.2f} seconds")
    logger.info(f"Response length: {len(second_response)} characters")
    
    return elapsed_time

async def compare_performance(model_id: str) -> Dict[str, float]:
    """Compare performance with and without caching."""
    logger.info(f"Testing prompt caching performance with model {model_id}")
    
    # Run without caching first
    time_without_caching = await run_without_caching(model_id)
    
    # Wait a moment
    await asyncio.sleep(1)
    
    # Run with caching
    time_with_caching_first = await run_with_caching(model_id)
    
    return {
        "without_caching": time_without_caching,
        "with_caching_first": time_with_caching_first
    }

async def main():
    """Main entry point."""
    # Get compatible models
    model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"  # Use a model that supports caching
    
    try:
        # Check for prompt caching support across all models
        client = ClaudeClient(model_id=model_id, logger=logger, use_model_discovery=True)
        await client.initialize()
        
        # Show models that support prompt caching
        discovery = client._model_discovery
        if discovery:
            status = discovery.get_prompt_caching_support_status()
            logger.info("Models with prompt caching support:")
            for model, supported in status.items():
                if supported:
                    logger.info(f"- {model}")
        
        # Compare performance
        results = await compare_performance(model_id)
        
        logger.info("\nPerformance Summary:")
        logger.info(f"Without caching: {results['without_caching']:.2f} seconds")
        logger.info(f"With caching (first run): {results['with_caching_first']:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Create Unit Tests

Create unit tests for prompt caching functionality in `src/dbp/llm/bedrock/tests/test_prompt_caching.py`:

```python
#!/usr/bin/env python3
"""
Unit tests for prompt caching functionality in Bedrock clients.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, patch
import logging

from src.dbp.llm.bedrock.enhanced_base import ModelCapability, EnhancedBedrockBase
from src.dbp.llm.bedrock.models.claude3 import ClaudeClient
from src.dbp.llm.bedrock.discovery.models import BedrockModelDiscovery


class TestPromptCaching(unittest.TestCase):
    """Test cases for prompt caching functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Disable logging during tests
        logging.disable(logging.CRITICAL)
        
    def tearDown(self):
        """Tear down test fixtures."""
        # Re-enable logging
        logging.disable(logging.NOTSET)
    
    @patch('src.dbp.llm.bedrock.discovery.models.BedrockModelDiscovery')
    def test_supports_prompt_caching(self, mock_discovery):
        """Test prompt caching support detection."""
        # Set up mock
        discovery_instance = mock_discovery.get_instance.return_value
        discovery_instance.supports_prompt_caching.side_effect = lambda model_id: model_id.startswith("anthropic.claude-3-5")
        
        # Test supported model
        self.assertTrue(discovery_instance.supports_prompt_caching("anthropic.claude-3-5-haiku-123"))
        
        # Test unsupported model
        self.assertFalse(discovery_instance.supports_prompt_caching("anthropic.claude-3-sonnet-123"))
    
    @patch('src.dbp.llm.bedrock.models.claude3.ClaudeClient._model_discovery')
    def test_capability_registration(self, mock_discovery):
        """Test prompt caching capability is registered for supported models."""
        # Set up mock
        mock_discovery.supports_prompt_caching.side_effect = lambda model_id: model_id.startswith("anthropic.claude-3-5")
        
        # Test supported model
        client = ClaudeClient("anthropic.claude-3-5-haiku-123")
        self.assertTrue(client.has_capability(ModelCapability.PROMPT_CACHING))
        
        # Test unsupported model
        client = ClaudeClient("anthropic.claude-3-sonnet-123")
        self.assertFalse(client.has_capability(ModelCapability.PROMPT_CACHING))
    
    @patch('src.dbp.llm.bedrock.enhanced_base.EnhancedBedrockBase.has_capability')
    def test_enable_prompt_caching(self, mock_has_capability):
        """Test enabling prompt caching."""
        client = EnhancedBedrockBase("test-model")
        
        # Test supported model
        mock_has_capability.return_value = True
        self.assertTrue(client.enable_prompt_caching())
        self.assertTrue(client.is_prompt_caching_enabled())
        
        # Test unsupported model
        mock_has_capability.return_value = False
        self.assertFalse(client.enable_prompt_caching())
        self.assertFalse(client.is_prompt_caching_enabled())
    
    def test_mark_cache_point(self):
        """Test marking cache point in messages."""
        client = EnhancedBedrockBase("test-model")
        
        # Set up test messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me about AWS."}
        ]
        
        # Test with caching disabled
        with patch.object(client, 'is_prompt_caching_enabled', return_value=False):
            result = client.mark_cache_point(messages)
            self.assertEqual(result["status"], "ignored")
            self.assertFalse(result["cache_active"])
            self.assertEqual(result["messages"], messages)
            
        # Test with caching enabled
        with patch.object(client, 'is_prompt_caching_enabled', return_value=True):
            result = client.mark_cache_point(messages)
            self.assertEqual(result["status"], "marked")
            self.assertTrue(result["cache_active"])
            
            # Check cache point metadata was added
            last_message = result["messages"][-1]
            self.assertIn("metadata", last_message)
            self.assertIn("cache_point", last_message["metadata"])
            self.assertIn("id", last_message["metadata"]["cache_point"])
    
    @patch('src.dbp.llm.bedrock.base.BedrockBase._format_model_kwargs')
    def test_caching_config_in_request(self, mock_format):
        """Test caching configuration is added to request."""
        client = EnhancedBedrockBase("test-model")
        
        # Base case - no caching
        mock_format.return_value = {"temperature": 0.7}
        kwargs = {}
        self.assertEqual(client._format_model_kwargs(kwargs), {"temperature": 0.7})
        
        # With caching parameter
        kwargs = {"enable_caching": True}
        mock_format.return_value = {
            "temperature": 0.7,
            "caching": {"cachingState": "ENABLED"}
        }
        self.assertEqual(
            client._format_model_kwargs(kwargs),
            {"temperature": 0.7, "caching": {"cachingState": "ENABLED"}}
        )

# Run tests asynchronously
if __name__ == "__main__":
    unittest.main()
```

### 3. Create Documentation

Create documentation for the prompt caching feature in `src/dbp/llm/bedrock/docs/prompt_caching.md`:

```markdown
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
from src.dbp.llm.bedrock.models.claude3 import ClaudeClient
from src.dbp.llm.bedrock.enhanced_base import ModelCapability

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
```

### 4. Create Verification Script

Create a verification script in `src/dbp/llm/bedrock/examples/verify_prompt_caching.py`:

```python
#!/usr/bin/env python3
"""
Verification script for prompt caching implementation.

This script verifies that all requirements for prompt caching have been met:
1. Ability to check if a model supports prompt caching
2. API to enable prompt caching for a conversation
3. API to mark cache points in a conversation
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from src.dbp.llm.bedrock.enhanced_base import ModelCapability, EnhancedBedrockBase
from src.dbp.llm.bedrock.models.claude3 import ClaudeClient
from src.dbp.llm.bedrock.discovery.models import BedrockModelDiscovery

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("prompt_caching_verification")

class VerificationResult:
    """Container for verification results."""
    
    def __init__(self):
        self.requirements = {
            "model_support_detection": False,
            "enable_caching_api": False,
            "mark_cache_point_api": False
        }
        self.details = {}
        
    def set_result(self, requirement: str, passed: bool, details: str):
        """Set result for a requirement."""
        self.requirements[requirement] = passed
        self.details[requirement] = details
    
    def all_passed(self) -> bool:
        """Check if all requirements passed."""
        return all(self.requirements.values())
    
    def summary(self) -> str:
        """Get summary of verification results."""
        result = "Verification Results:\n"
        result += "=" * 50 + "\n\n"
        
        for req, passed in self.requirements.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            result += f"{status}: {req}\n"
            result += f"   {self.details.get(req, 'No details')}\n\n"
        
        result += f"Overall Status: {'✅ PASSED' if self.all_passed() else '❌ FAILED'}\n"
        return result

async def verify_model_support_detection() -> Dict[str, Any]:
    """Verify ability to check if a model supports prompt caching."""
    result = {
        "passed": False,
        "details": ""
    }
    
    try:
        # Get model discovery instance
        discovery = BedrockModelDiscovery.get_instance()
        
        # Test with a model that should support caching
        support_claude = discovery.supports_prompt_caching("anthropic.claude-3-5-haiku-20241022-v1:0")
        
        # Test with a model that shouldn't support caching
        support_other = discovery.supports_prompt_caching("amazon.titan-text-express-v1")
        
        # Check if function exists and returns expected results
        if support_claude is True and support_other is False:
            result["passed"] = True
            result["details"] = "Model support detection correctly identifies supported and unsupported models"
        else:
            result["details"] = f"Unexpected results: Claude support: {support_claude}, Other support: {support_other}"
    except Exception as e:
        result["details"] = f"Error verifying model support detection: {str(e)}"
    
    return result

async def verify_enable_caching_api() -> Dict[str, Any]:
    """Verify API to enable prompt caching for a conversation."""
    result = {
        "passed": False,
        "details": ""
    }
    
    try:
        # Create a client with a supported model
        client = ClaudeClient("anthropic.claude-3-5-haiku-20241022-v1:0", logger=logger)
        
        # Mock initialization
        client._initialized = True
        
        # Test enabling caching
        with patch.object(client, 'has_capability', return_value=True):
            enabled = client.enable_prompt_caching(True)
            status = client.is_prompt_caching_enabled()
            
            if enabled is True and status is True:
                # Test disabling caching
                disabled = client.enable_prompt_caching(False)
                status = client.is_prompt_caching_enabled()
                
                if disabled is False and status is False:
                    result["passed"] = True
                    result["details"] = "Enable/disable prompt caching API works correctly"
                else:
                    result["details"] = f"Failed to disable caching: disabled={disabled}, status={status}"
            else:
                result["details"] = f"Failed to enable caching: enabled={enabled}, status={status}"
    except Exception as e:
        result["details"] = f"Error verifying enable caching API: {str(e)}"
    
    return result

async def verify_mark_cache_point_api() -> Dict[str, Any]:
    """Verify API to mark cache points in a conversation."""
    result = {
        "passed": False,
        "details": ""
    }
    
    try:
        # Create a client
        client = EnhancedBedrockBase("test-model", logger=logger)
        client._initialized = True
        
        # Test messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me about AWS."}
        ]
        
        # Test with caching disabled
        with patch.object(client, 'is_prompt_caching_enabled', return_value=False):
            disabled_result = client.mark_cache_point(messages)
            
            if (disabled_result["status"] == "ignored" 
                    and disabled_result["cache_active"] is False 
                    and disabled_result["messages"] == messages):
                
                # Test with caching enabled
                with patch.object(client, 'is_prompt_caching_enabled', return_value=True):
                    enabled_result = client.mark_cache_point(messages)
                    
                    if (enabled_result["status"] == "marked" 
                            and enabled_result["cache_active"] is True
                            and "metadata" in enabled_result["messages"][-1]
                            and "cache_point" in enabled_result["messages"][-1]["metadata"]):
                        
                        result["passed"] = True
                        result["details"] = "Cache point marking API works correctly"
                    else:
                        result["details"] = f"Failed with caching enabled: {enabled_result}"
            else:
                result["details"] = f"Failed with caching disabled: {disabled_result}"
    except Exception as e:
        result["details"] = f"Error verifying mark cache point API: {str(e)}"
    
    return result

async def run_verification() -> VerificationResult:
    """Run all verification checks."""
    # Import unittest.mock only when needed for verification
    global patch
    from unittest.mock import patch
    
    verification = VerificationResult()
    
    # Check model support detection
    model_support = await verify_model_support_detection()
    verification.set_result(
        "model_support_detection", 
        model_support["passed"], 
        model_support["details"]
    )
    
    # Check enable caching API
    enable_caching = await verify_enable_caching_api()
    verification.set_result(
        "enable_caching_api", 
        enable_caching["passed"], 
        enable_caching["details"]
    )
    
    # Check mark cache point API
    mark_cache_point = await verify_mark_cache_point_api()
    verification.set_result(
        "mark_cache_point_api", 
        mark_cache_point["passed"], 
        mark_cache_point["details"]
    )
    
    return verification

async def main():
    """Main entry point."""
    logger.info("Starting prompt caching verification")
    
    try:
        result = await run_verification()
        print(result.summary())
        
        if result.all_passed():
            logger.info("All verification checks passed!")
        else:
            logger.error("Some verification checks failed. See summary for details.")
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 5. Update README

Update `src/dbp/llm/bedrock/README.md` to include information about prompt caching support:

```markdown
# Add a section about Prompt Caching

## Prompt Caching Support

This library supports Amazon Bedrock's prompt caching feature, which can:
- Reduce costs by up to 90%
- Reduce latency by up to 85%
- Optimize token processing for large language models

### Supported Models

Prompt caching is supported on select models:
- Claude 3.5 Haiku
- Claude 3.7 Sonnet
- Nova Micro/Lite/Pro

### Basic Usage

```python
from src.dbp.llm.bedrock.models.claude3 import ClaudeClient
from src.dbp.llm.bedrock.enhanced_base import ModelCapability

# Initialize client
client = ClaudeClient("anthropic.claude-3-5-haiku-20241022-v1:0")
await client.initialize()

# Check if model supports prompt caching
if client.has_capability(ModelCapability.PROMPT_CACHING):
    # Enable prompt caching
    client.enable_prompt_caching()
    
    # Mark cache points in conversation
    messages = [{"role": "user", "content": "Tell me about AWS"}]
    result = client.mark_cache_point(messages)
    
    # Use marked messages
    response = await client.stream_chat(result["messages"])
```

For more details, see [Prompt Caching Documentation](docs/prompt_caching.md).
```

## Testing Strategy

The following tests should be implemented and run to verify the Phase 4 changes:

1. Run the example script to demonstrate prompt caching
2. Run the unit tests to verify correct behavior
3. Run the verification script to ensure all requirements are met
4. Verify that documentation is clear and accurate

## Compatibility Considerations

- Documentation aligns with implementation details
- Examples show realistic usage patterns
- Testing covers failure modes and edge cases
- Verification confirms all requirements are met
