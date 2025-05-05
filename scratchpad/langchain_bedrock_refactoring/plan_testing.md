# Phase 6: Update Tests and Examples

## Current Test Structure

The current test suite likely includes tests for both the legacy `EnhancedBedrockBase` implementation and the newer LangChain-based `EnhancedChatBedrockConverse` implementation. With the refactoring, we need to update the tests to focus exclusively on the LangChain-based implementation and its model-specific extensions.

## Test Update Strategy

### Unit Tests

1. **Base Class Tests**:
   - Update existing tests for `EnhancedChatBedrockConverse` to use the new `_extract_text_from_chunk` method
   - Verify that the original `extract_text_from_chunk` static method still works as expected for backward compatibility
   - Test the default implementation of `_extract_text_from_chunk` to ensure it correctly delegates to the static method

2. **Model-Specific Tests**:
   - Create unit tests for `ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk`
   - Create unit tests for `NovaEnhancedChatBedrockConverse._extract_text_from_chunk`
   - Test with a variety of input formats including edge cases

3. **Client Factory Tests**:
   - Update tests for `BedrockClientFactory.create_langchain_chatbedrock` to verify it creates the correct model-specific class
   - Remove tests for the now-deleted `create_client` method
   - Test with various model IDs to ensure correct class selection

### Mock Tests

Create mock tests with predefined response formats:

```python
def test_claude_extract_text():
    # Test Claude delta format
    claude_chunk = {"delta": {"text": "Hello world"}}
    result = ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk(claude_chunk)
    assert result == "Hello world"
    
    # Test Claude completion format
    claude_completion = {"completion": "Completion text"}
    result = ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk(claude_completion)
    assert result == "Completion text"
    
    # Test fallback to parent implementation
    other_format = {"text": "Generic text"}
    result = ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk(other_format)
    assert result == "Generic text"

def test_nova_extract_text():
    # Test Nova output format
    nova_chunk = {"output": {"text": "Hello from Nova"}}
    result = NovaEnhancedChatBedrockConverse._extract_text_from_chunk(nova_chunk)
    assert result == "Hello from Nova"
    
    # Test Nova chunk format with JSON
    json_bytes = json.dumps({"text": "Nova JSON chunk"})
    nova_json_chunk = {"chunk": {"bytes": json_bytes}}
    result = NovaEnhancedChatBedrockConverse._extract_text_from_chunk(nova_json_chunk)
    assert result == "Nova JSON chunk"
    
    # Test Nova chunk format with plain text
    nova_text_chunk = {"chunk": {"bytes": "Plain text chunk"}}
    result = NovaEnhancedChatBedrockConverse._extract_text_from_chunk(nova_text_chunk)
    assert result == "Plain text chunk"
```

### Integration Tests

1. **Streaming Tests**:
   - Test streaming with Claude models to verify text extraction works properly
   - Test streaming with Nova models to verify text extraction works properly
   - Test the streaming methods `stream_text` and `astream_text` with both model types

2. **Client Factory Integration**:
   - Test end-to-end flow from factory creation to text extraction

### Example Code Updates

Update any examples that demonstrate the use of Bedrock models:

1. **Basic Usage Examples**:
   - Replace examples using `create_client` with examples using `create_langchain_chatbedrock`
   - Update code snippets in documentation

2. **Streaming Examples**:
   - Ensure streaming examples use the updated API
   - Add examples showing model-specific features where applicable

## Test Cases to Add

### Edge Cases

1. **Empty and None Inputs**:
   - Test behavior with empty strings, empty dictionaries, None values

2. **Malformed Responses**:
   - Test with incomplete or malformed response structures
   - Verify graceful handling of unexpected formats

3. **Mixed Format Responses**:
   - Test with responses that combine elements from different formats
   - Verify the extraction logic prioritizes correctly

4. **Streaming Error Handling**:
   - Test with simulated network errors, API throttling
   - Verify retry logic works correctly

## Test File Updates

The following test files will likely need updates:

1. `tests/test_langchain_wrapper.py`: Update to test the new abstract method pattern
2. `tests/test_model_clients.py`: Update to test the new model-specific classes
3. `tests/test_client_factory.py`: Update to remove tests for the deleted method

## New Test Files to Create

1. `tests/test_claude_client.py`: Tests for the Claude-specific implementation
2. `tests/test_nova_client.py`: Tests for the Nova-specific implementation

## Test Environment Setup

Ensure the test environment includes:

1. Mock responses for both Claude and Nova format chunks
2. Test fixtures for creating client instances
3. Mock AWS clients to avoid actual API calls during tests

## Documentation Updates

Update test documentation to:

1. Reflect the new implementation structure
2. Provide examples of how to test custom model implementations
3. Explain how to mock model responses for testing
