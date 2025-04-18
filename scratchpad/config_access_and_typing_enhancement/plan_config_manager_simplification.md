# Phase 5: ConfigurationManager Simplification

## Implementation Plan for ConfigurationManager Simplification

### Current State

Currently, the ConfigurationManager class:
- Maintains both a Pydantic model (`_config`) and a raw dictionary representation (`_raw_config_dict`)
- Processes configuration through multiple dictionary manipulations
- Has methods for both dictionary-based and Pydantic model-based access
- Contains complex logic for handling hierarchical configuration merges using dictionaries
- Includes template resolution and value conversion functions

### Goal

Simplify ConfigurationManager to exclusively use Pydantic models for configuration representation, eliminating dict-based configuration management.

### Detailed Implementation Steps

#### 1. Remove Dictionary-Based Storage

Remove or refactor these dictionary-based storage variables:

```python
# Remove or refactor these attributes
self._raw_config_dict: Dict[str, Any] = {}  # Holds merged raw data before validation
```

#### 2. Simplify Configuration Access Methods

Refactor the `get()` method to use direct Pydantic model access:

```python
def get(self, key: str, resolve_templates: bool = True) -> Any:
    """
    [Function intent]
    Retrieves a configuration value using dot notation (e.g., 'database.type').
    Automatically resolves any template variables in string values.
    
    [Implementation details]
    Uses direct attribute access on the Pydantic AppConfig model.
    Falls back to default configuration if not initialized.
    
    [Design principles]
    Type-safe configuration access with template resolution.
    
    Args:
        key: The configuration key in dot notation.
        resolve_templates: Whether to resolve template variables in string values.

    Returns:
        The configuration value with template variables resolved.
        
    Raises:
        ValueError: If the configuration key doesn't exist.
    """
    if not self.initialized_flag:
        # Get defaults from AppConfig
        config = AppConfig()
    else:
        config = self._config
        
    # Navigate through the Pydantic model hierarchy
    parts = key.split('.')
    value = config
    
    try:
        for part in parts:
            value = getattr(value, part)
            
        # Resolve template variables in string values if requested
        if resolve_templates and isinstance(value, str):
            value = self.resolve_template_string(value)
            
        return value
    except AttributeError as e:
        # Create a more descriptive error message
        path_so_far = ".".join(parts[:parts.index(part) if part in parts else 0])
        if path_so_far:
            error_message = f"Configuration key '{key}' not found. '{path_so_far}' exists but has no attribute '{part}'."
        else:
            error_message = f"Configuration key '{key}' not found in configuration."
        
        self.logger.error(error_message)
        raise ValueError(error_message) from e
```

#### 3. Remove Dictionary Conversion Methods

Remove methods that convert between dictionaries and Pydantic models:

```python
# Remove or refactor these methods
def _nested_dict_from_keys(self, flat_dict: Dict[str, Any]) -> Dict[str, Any]:
    # Implementation...

def _merge_dict(self, target: Dict[str, Any], source: Dict[str, Any]):
    # Implementation...

def as_dict(self) -> Dict[str, Any]:
    # Implementation...

def get_raw_merged_config(self) -> Dict[str, Any]:
    # Implementation...
```

#### 4. Simplify Configuration Loading Process

Refactor the configuration loading process to work directly with Pydantic models:

```python
def _apply_configuration_hierarchy(self):
    """
    [Function intent]
    Applies configuration from all sources and validates using the Pydantic schema.
    
    [Implementation details]
    Creates a base AppConfig instance and sequentially applies configuration from
    different sources directly to the Pydantic model.
    
    [Design principles]
    Direct Pydantic model manipulation without intermediate dictionaries.
    Proper validation at each configuration layer.
    """
    logger.debug("Applying configuration hierarchy...")
    
    # Start with default configuration
    config = AppConfig()
    
    # Apply configurations in order of precedence
    try:
        # 1. Apply standard config files
        for file_path in sorted(self._config_files_data.keys()):
            if ".dbp" not in file_path:  # Not a project config
                self._apply_config_data_to_model(config, self._config_files_data[file_path])
        
        # 2. Apply project config
        project_config_path_str = next((p for p in self._config_files_data if ".dbp" in p), None)
        if project_config_path_str:
            self._apply_config_data_to_model(config, self._config_files_data[project_config_path_str])
            
        # 3. Apply environment variables
        if self._env_vars:
            for key, value in self._env_vars.items():
                self._set_config_attr_by_path(config, key, self._convert_value(value))
                
        # 4. Apply CLI arguments
        if self._cli_args:
            for key, value in self._cli_args.items():
                self._set_config_attr_by_path(config, key, self._convert_value(value))
                
        # Store the final validated config
        self._config = config
        logger.debug("Configuration validated successfully against schema.")
        
    except ValidationError as e:
        logger.error(f"Configuration validation failed. Using default values. Errors:\n{e}")
        # Fallback to default configuration on validation error
        self._config = AppConfig()
    
def _apply_config_data_to_model(self, config: AppConfig, data: Dict[str, Any]):
    """Helper method to apply config data to a Pydantic model"""
    for key, value in data.items():
        if isinstance(value, dict):
            # Get the corresponding attribute
            try:
                attr = getattr(config, key)
                # Recursively apply nested configuration
                for subkey, subvalue in value.items():
                    self._set_config_attr_by_path(attr, subkey, subvalue)
            except AttributeError:
                logger.warning(f"Configuration section '{key}' not found in schema")
        else:
            # Set direct attribute
            try:
                setattr(config, key, value)
            except (AttributeError, ValidationError) as e:
                logger.warning(f"Failed to set configuration '{key}': {e}")
                
def _set_config_attr_by_path(self, obj, path: str, value: Any):
    """Helper method to set a nested attribute using dot notation path"""
    parts = path.split('.')
    for i, part in enumerate(parts[:-1]):
        try:
            obj = getattr(obj, part)
        except AttributeError:
            logger.warning(f"Couldn't navigate to '{part}' in configuration path '{path}'")
            return
    
    try:
        setattr(obj, parts[-1], value)
    except (AttributeError, ValidationError) as e:
        logger.warning(f"Failed to set configuration '{path}': {e}")
```

#### 5. Adapt Template Resolution

Update the template resolution logic to work with the simplified approach:

```python
def resolve_template_string(self, template_str: str, max_depth: int = 10) -> str:
    """
    [Function intent]
    Resolves a string containing template variables in the format ${key},
    where key is a configuration key in dot notation.
    
    [Implementation details]
    Uses the direct attribute access approach to resolve references.
    
    [Design principles]
    Clean template resolution with proper recursion control.
    
    Args:
        template_str: The string containing template variables.
        max_depth: Maximum recursion depth for nested templates.
        
    Returns:
        The resolved string with all template variables replaced with their values.
    """
    # Implementation remains largely the same, but use the updated get() method
    # for resolving referenced keys
```

#### 6. Update `set()` Method

Refactor the `set()` method to use Pydantic directly:

```python
def set(self, key: str, value: Any) -> bool:
    """
    [Function intent]
    Sets a configuration value at runtime using dot notation.
    
    [Implementation details]
    Uses direct attribute setting on the Pydantic AppConfig model
    with validation.
    
    [Design principles]
    Type-safe configuration updates with validation.
    
    Args:
        key: The configuration key in dot notation.
        value: The value to set.

    Returns:
        True if the value was set and validated successfully, False otherwise.
    """
    if not self.initialized_flag:
        logger.error("Cannot set configuration before initialization.")
        return False
        
    with self._lock:
        # Keep a backup of the current config
        original_config = self._config
        
        try:
            # Create a copy of the current config 
            config_dict = self._config.dict()
            new_config = AppConfig(**config_dict)
            
            # Set the value on the copy
            self._set_config_attr_by_path(new_config, key, value)
            
            # If we got here without exceptions, the update is valid
            self._config = new_config
            logger.info(f"Configuration value set and validated: {key} = {value}")
            return True
            
        except (AttributeError, ValidationError) as e:
            logger.error(f"Validation failed when setting '{key}' to '{value}'. Change reverted. Errors:\n{e}")
            # Revert is implicit as self._config was not updated
            return False
```

### Impact Analysis

The ConfigurationManager simplification:
- Reduces code complexity by eliminating dictionary manipulations
- Provides cleaner, more direct access to the underlying Pydantic model
- Improves type safety by working directly with typed models
- Eliminates redundant data structures and conversions
- Makes the code more maintainable and easier to understand
- Aligns with the directive to manage only Pydantic-represented configurations

### Testing Strategy

- Test configuration loading from different sources
- Verify the refactored `get()` method works with different path types
- Test template resolution with the updated implementation
- Ensure the `set()` method correctly validates and applies changes
- Verify proper error handling for invalid configurations
