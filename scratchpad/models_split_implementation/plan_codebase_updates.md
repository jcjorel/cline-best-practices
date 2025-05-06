# Codebase Reference Updates for models.py Split

This document details the necessary updates to the codebase references after splitting `models.py` into `models_core.py` and `models_capabilities.py`.

## Identified Import References

Based on the search of the codebase, these files import `BedrockModelDiscovery` from `models.py` and will need updates:

### Direct Imports from models.py

1. `src/dbp/llm/bedrock/__init__.py`
2. `src/dbp/llm/bedrock/client_factory.py`
3. `src/dbp/llm/bedrock/examples/display_model_availability.py`
4. `src/dbp/llm/bedrock/examples/langchain_model_discovery_example.py`
5. `src/dbp/llm/bedrock/examples/langchain_client_factory_example.py`
6. `src/dbp/llm/bedrock/discovery/profiles.py`

### Test Files with Patch Decorators

1. `src/dbp/llm/bedrock/tests/test_client_factory.py`

## Update Strategy

For all files, we will update the imports to reference `BedrockModelCapabilities` instead of `BedrockModelDiscovery`, since the capabilities class provides all functionality of the original class.

### Import Update Patterns

#### Absolute Imports

```python
# Current:
from dbp.llm.bedrock.discovery.models import BedrockModelDiscovery

# Update to:
from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery
```

#### Relative Imports

```python
# Current:
from ..discovery.models import BedrockModelDiscovery

# Update to:
from ..discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery
```

#### Special Case: Within discovery Package

```python
# Current:
from .models import BedrockModelDiscovery

# Update to:
from .models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery
```

### Patch Decorator Updates

```python
# Current:
@patch('dbp.llm.bedrock.discovery.models.BedrockModelDiscovery.get_instance')

# Update to:
@patch('dbp.llm.bedrock.discovery.models_capabilities.BedrockModelCapabilities.get_instance')
```

## Detailed File Updates

### 1. src/dbp/llm/bedrock/__init__.py

- Update import statement
- Update __all__ list to include both `BedrockModelDiscovery` and `BedrockModelCapabilities`

### 2. src/dbp/llm/bedrock/client_factory.py

- Update import statement
- No changes needed to method calls as we use the `as BedrockModelDiscovery` alias

### 3. Example Files

For all three example files:
- Update import statements
- No changes needed to method calls

### 4. src/dbp/llm/bedrock/discovery/profiles.py

- Special handling for conditional import
- Update from `.models` to `.models_capabilities`

### 5. src/dbp/llm/bedrock/tests/test_client_factory.py

- Update all patch decorators
- The patch decorators need to point to the new class location and name

## Testing Strategy

After all updates, we need to run the test suite to verify:
1. All imports resolve correctly
2. The singleton pattern works properly
3. All functionality is preserved

If any test failures occur, they will likely be related to:
- Incorrect import paths
- Issues with the singleton pattern across classes
- Missing methods in the extracted classes

## Fallback Plan

If issues arise with the inheritance approach, we have alternative options:
1. Update imports to use `models_core.py` for files that only need core functionality
2. Consider a composition approach instead of inheritance if needed
