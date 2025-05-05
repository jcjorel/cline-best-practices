# LangChain Bedrock Integration Refactoring

⚠️ **CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN**

## Documentation Files

- [src/dbp/llm/bedrock/langchain_wrapper.py](../../../src/dbp/llm/bedrock/langchain_wrapper.py): Contains the current implementation of `EnhancedChatBedrockConverse` and the mixed approach to chunk extraction.
- [src/dbp/llm/bedrock/models/claude3.py](../../../src/dbp/llm/bedrock/models/claude3.py): Contains the current implementation of `ClaudeClient` extending `EnhancedBedrockBase`.
- [src/dbp/llm/bedrock/models/nova.py](../../../src/dbp/llm/bedrock/models/nova.py): Contains the current implementation of `NovaClient` extending `EnhancedBedrockBase`.
- [src/dbp/llm/bedrock/client_factory.py](../../../src/dbp/llm/bedrock/client_factory.py): Contains both the LangChain-oriented `create_langchain_chatbedrock` method and the legacy `create_client` method.
- [src/dbp/llm/bedrock/enhanced_base.py](../../../src/dbp/llm/bedrock/enhanced_base.py): The base class for the legacy client implementation to be removed.
- [src/dbp/llm/bedrock/base.py](../../../src/dbp/llm/bedrock/base.py): The root base class for the legacy client implementation to be removed.

## Refactoring Context

Currently, our LLM module supports two parallel approaches:

1. **Legacy Approach**: Uses `EnhancedBedrockBase` classes for direct Bedrock API integration.
2. **LangChain Approach**: Uses `EnhancedChatBedrockConverse` extending LangChain's `ChatBedrockConverse` class.

Our task is to refactor the code to:
1. Drop support for the legacy approach completely
2. Reuse model-specific logic from `nova.py` and `claude3.py` within the LangChain approach
3. Fix the design issue in `langchain_wrapper.py` where the `extract_text_from_chunk` method mixes different model-specific extraction logics

## Implementation Plan

The refactoring will be conducted in the following sequential phases:

### Phase 1: Update `langchain_wrapper.py`

Modify the `EnhancedChatBedrockConverse` class to make the text extraction extensible through an abstract method pattern.

### Phase 2: Refactor `claude3.py`

Create a new `ClaudeEnhancedChatBedrockConverse` class that extends `EnhancedChatBedrockConverse` and implements Claude-specific text extraction.

### Phase 3: Refactor `nova.py`

Create a new `NovaEnhancedChatBedrockConverse` class that extends `EnhancedChatBedrockConverse` and implements Nova-specific text extraction.

### Phase 4: Update `client_factory.py`

Remove the legacy `create_client` method and update the factory to create model-specific LangChain classes.

### Phase 5: Delete Legacy Files

Delete `enhanced_base.py` and `base.py` files as they are no longer needed.

### Phase 6: Update Tests and Examples

Update any tests or examples to use the new LangChain-based approach.

## Detailed Plan Files

- [plan_progress.md](./plan_progress.md): Tracks the progress of the implementation.
- [plan_langchain_wrapper.md](./plan_langchain_wrapper.md): Details the changes needed for `langchain_wrapper.py`.
- [plan_claude3.md](./plan_claude3.md): Details the changes needed for `claude3.py`.
- [plan_nova.md](./plan_nova.md): Details the changes needed for `nova.py`.
- [plan_client_factory.md](./plan_client_factory.md): Details the changes needed for `client_factory.py`.
- [plan_file_removal.md](./plan_file_removal.md): Details the files to be removed.
- [plan_testing.md](./plan_testing.md): Details the testing approach.

## Benefits of the Refactoring

1. **Cleaner Code Structure**: Each model type will have its own specific implementation for chunk extraction.
2. **Simplified Inheritance Hierarchy**: Direct inheritance from LangChain classes instead of our own custom hierarchy.
3. **Easier Maintenance**: Model-specific changes can be made in isolation without affecting other models.
4. **Code Reduction**: Elimination of duplicate code paths and legacy implementations.
5. **Consistent API**: All models now use the LangChain interface consistently.
