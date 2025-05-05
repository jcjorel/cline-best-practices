# Phase 5: Delete Legacy Files

## Files to Delete

As part of the refactoring to move completely to the LangChain-based approach, we need to remove the legacy implementation files that are no longer needed:

1. **`src/dbp/llm/bedrock/base.py`**: The base class for the legacy implementation that provided direct Bedrock API access.
2. **`src/dbp/llm/bedrock/enhanced_base.py`**: The enhanced base class that extended the base class with additional features.

## Verification Steps Before Deletion

Before deleting these files, it is essential to verify:

1. All functionality that was previously provided by these files has been migrated to the LangChain-based approach.
2. No other parts of the codebase are still importing or using these files.
3. All tests that depended on these files have been updated to use the new implementation.

## Search for References

Run a search across the codebase to identify any remaining references to the classes defined in these files:

```bash
# Search for references to BedrockBase
grep -r "BedrockBase" --include="*.py" src/

# Search for references to EnhancedBedrockBase
grep -r "EnhancedBedrockBase" --include="*.py" src/

# Search for imports of the files
grep -r "from .*.base import" --include="*.py" src/
grep -r "from .*.enhanced_base import" --include="*.py" src/
```

## Update References

Any references found should be updated to use the LangChain-based implementation:

1. Replace `BedrockBase` with `EnhancedChatBedrockConverse`
2. Replace `EnhancedBedrockBase` with `EnhancedChatBedrockConverse`
3. Update imports to point to `langchain_wrapper.py` instead of `base.py` or `enhanced_base.py`
4. Update any code that uses methods specific to the legacy classes to use the equivalent methods in the new classes

## Deletion Process

Once all references have been updated, delete the files:

```bash
rm src/dbp/llm/bedrock/base.py
rm src/dbp/llm/bedrock/enhanced_base.py
```

## Impact Assessment

### Positive Impacts

1. **Code Simplification**: Removing the legacy implementation simplifies the codebase by eliminating parallel implementations.
2. **Reduced Maintenance Burden**: Single implementation path makes future updates easier.
3. **Better Integration**: Direct integration with LangChain provides access to its ecosystem of tools.

### Potential Risks

1. **Breaking Changes**: Code that directly referenced the legacy classes will need to be updated.
2. **Model-Specific Features**: Some model-specific features from the legacy implementation might need to be migrated to the LangChain implementation.
3. **Interface Differences**: The interfaces between the legacy and LangChain implementations might differ, requiring adaptation in client code.

## Backward Compatibility Considerations

While we're dropping support for the legacy implementation, we should ensure that any public APIs that were widely used are still available through the new implementation to minimize the impact on client code. This might involve adding wrapper methods or adapters if necessary.
