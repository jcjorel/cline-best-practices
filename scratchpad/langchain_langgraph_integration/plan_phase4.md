# Phase 4: Prompt Management

This phase implements the prompt management system for the LangChain/LangGraph integration. It focuses on loading prompts from the doc/llm/prompts directory, handling template substitution, and implementing a caching system for optimal performance.

## Objectives

1. Create a prompt loading mechanism for files in doc/llm/prompts
2. Implement template variable substitution
3. Build a prompt versioning and caching system
4. Implement validation and error reporting for prompts

## PromptManager Implementation

Create the prompt manager class in `src/dbp/llm/common/prompt_manager.py`:

```python
import os
import re
import logging
from typing import Dict, Any, Optional, List, Set
import hashlib
from pathlib import Path
import datetime
from collections import defaultdict

from src.dbp.llm.common.exceptions import PromptError, PromptNotFoundError, PromptRenderingError

class PromptManager:
    """
    [Class intent]
    Manages loading, caching, and rendering of prompt templates stored in the
    doc/llm/prompts directory. This centralizes prompt management to ensure
    consistent prompt handling throughout the application.
    
    [Design principles]
    - Single source of truth for all prompt templates
    - Clear separation between template storage and template rendering
    - Support for variable substitution in templates
    - Efficient caching for performance optimization
    - Version tracking for templates
    
    [Implementation details]
    - Loads templates from the doc/llm/prompts directory
    - Implements a caching mechanism for rendered prompts
    - Uses simple variable substitution with validation
    - Maintains prompt versions based on content hashes
    """
    
    # Template variable pattern: {{variable_name}}
    VARIABLE_PATTERN = r'{{([a-zA-Z0-9_]+)}}'
    
    def __init__(self, prompts_dir: str = None, cache_size: int = 100):
        """
        [Method intent]
        Initialize the prompt manager with configuration options.
        
        [Design principles]
        - Configurable prompt directory location
        - Customizable caching parameters
        - Default sensible values for minimal configuration
        
        [Implementation details]
        - Sets up the prompts directory path
        - Initializes caching structures
        - Prepares for lazy loading of templates
        
        Args:
            prompts_dir: Directory containing prompt templates (default: doc/llm/prompts)
            cache_size: Maximum number of rendered prompts to cache
        """
        # Set prompts directory (default if not specified)
        self.prompts_dir = prompts_dir or os.path.join('doc', 'llm', 'prompts')
        
        # Check if directory exists
        if not os.path.isdir(self.prompts_dir):
            raise PromptError(f"Prompts directory not found: {self.prompts_dir}")
        
        # Initialize caching structures
        self.cache_size = cache_size
        self._template_cache: Dict[str, str] = {}  # name -> template content
        self._template_hashes: Dict[str, str] = {}  # name -> content hash
        self._template_variables: Dict[str, Set[str]] = {}  # name -> required variables
        self._rendered_cache: Dict[str, str] = {}  # cache_key -> rendered prompt
        self._rendered_timestamps: Dict[str, float] = {}  # cache_key -> timestamp
        
        # Initialize logger
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Track loaded prompt versions
        self._versions: Dict[str, str] = {}  # name -> version hash
        
        # Load prompt index on initialization
        self._load_prompt_index()
    
    def _load_prompt_index(self) -> None:
        """
        [Method intent]
        Load the index of available prompts for efficient lookup.
        
        [Design principles]
        - Lazy loading of prompt content
        - Early validation of prompt existence
        - Version tracking for prompts
        
        [Implementation details]
        - Scans the prompts directory for markdown files
        - Builds an index of available prompts
        - Does not load content until needed
        """
        self._available_prompts = {}
        
        # Scan prompts directory for markdown files
        for file_path in Path(self.prompts_dir).glob('*.md'):
            prompt_name = file_path.stem  # Filename without extension
            self._available_prompts[prompt_name] = str(file_path)
            
        self._logger.info(f"Found {len(self._available_prompts)} prompt templates")
    
    def _load_template(self, name: str) -> str:
        """
        [Method intent]
        Load a prompt template from disk.
        
        [Design principles]
        - Load on demand to minimize memory usage
        - Cache loaded templates for performance
        - Track template versions for change detection
        
        [Implementation details]
        - Checks if template exists in the index
        - Loads template content from file
        - Computes hash for version tracking
        - Extracts required variables
        
        Args:
            name: Name of the prompt template to load
            
        Returns:
            str: Template content
            
        Raises:
            PromptNotFoundError: If the prompt does not exist
        """
        # Check if already cached
        if name in self._template_cache:
            return self._template_cache[name]
        
        # Check if prompt exists
        if name not in self._available_prompts:
            raise PromptNotFoundError(f"Prompt template not found: {name}")
        
        # Load template content from file
        template_path = self._available_prompts[name]
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                template_content = file.read()
                
            # Compute hash for version tracking
            content_hash = hashlib.md5(template_content.encode('utf-8')).hexdigest()
            self._template_hashes[name] = content_hash
            self._versions[name] = content_hash[:8]  # First 8 chars as version
            
            # Extract required variables
            self._template_variables[name] = set(
                re.findall(self.VARIABLE_PATTERN, template_content)
            )
            
            # Cache template content
            self._template_cache[name] = template_content
            
            return template_content
        except Exception as e:
            raise PromptError(f"Failed to load prompt template '{name}': {str(e)}")
    
    def _generate_cache_key(self, name: str, variables: Dict[str, Any]) -> str:
        """
        [Method intent]
        Generate a unique cache key for a rendered prompt.
        
        [Design principles]
        - Deterministic key generation for reliable caching
        - Include all relevant factors in key
        
        [Implementation details]
        - Combines prompt name, version, and variable values
        - Uses sorted keys for consistent ordering
        - Handles different variable types
        
        Args:
            name: Name of the prompt template
            variables: Dictionary of variables for substitution
            
        Returns:
            str: Unique cache key
        """
        # Get template version
        version = self._versions.get(name, "unknown")
        
        # Create a representation of the variables for hashing
        var_str = "".join(
            f"{k}:{str(v)}" for k, v in sorted(variables.items())
        )
        
        # Combine name, version, and variables
        combined = f"{name}:{version}:{var_str}"
        
        # Generate hash
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """
        [Method intent]
        Render a template by substituting variables.
        
        [Design principles]
        - Simple and efficient variable substitution
        - Clear error reporting for missing variables
        - Type conversion for common variable types
        
        [Implementation details]
        - Uses regex to find and replace variables
        - Validates all required variables are provided
        - Converts variables to strings for substitution
        
        Args:
            template: Template content with variables
            variables: Dictionary of variables for substitution
            
        Returns:
            str: Rendered prompt with variables substituted
            
        Raises:
            PromptRenderingError: If rendering fails
        """
        try:
            # Extract required variables
            required_vars = set(re.findall(self.VARIABLE_PATTERN, template))
            
            # Check all required variables are provided
            missing_vars = required_vars - set(variables.keys())
            if missing_vars:
                raise PromptRenderingError(
                    f"Missing required variables: {', '.join(missing_vars)}"
                )
            
            # Perform substitution
            rendered = template
            for var_name, value in variables.items():
                # Convert value to string
                str_value = str(value)
                
                # Substitute variable
                pattern = f"{{{{{var_name}}}}}"
                rendered = rendered.replace(pattern, str_value)
            
            return rendered
        except Exception as e:
            if not isinstance(e, PromptRenderingError):
                e = PromptRenderingError(f"Failed to render template: {str(e)}")
            raise e
    
    def _manage_cache(self) -> None:
        """
        [Method intent]
        Manage the rendered prompt cache to prevent excessive memory usage.
        
        [Design principles]
        - Limit cache size to configured maximum
        - Remove least recently used entries first
        - Efficient cache management
        
        [Implementation details]
        - Checks if cache exceeds size limit
        - Sorts entries by timestamp
        - Removes oldest entries until within size limit
        """
        # Check if cache is too large
        if len(self._rendered_cache) <= self.cache_size:
            return
        
        # Sort by timestamp (oldest first)
        sorted_keys = sorted(
            self._rendered_timestamps.keys(),
            key=lambda k: self._rendered_timestamps[k]
        )
        
        # Remove oldest entries
        to_remove = len(self._rendered_cache) - self.cache_size
        for key in sorted_keys[:to_remove]:
            del self._rendered_cache[key]
            del self._rendered_timestamps[key]
    
    def get_prompt(self, name: str, variables: Dict[str, Any] = None) -> str:
        """
        [Method intent]
        Get a rendered prompt by name with variable substitution.
        
        [Design principles]
        - Simple interface for prompt access
        - Efficient caching for performance
        - Clear error messages for failures
        
        [Implementation details]
        - Loads template if not already cached
        - Checks cache for previously rendered prompt
        - Renders prompt with variables if not cached
        - Updates cache with new rendering
        
        Args:
            name: Name of the prompt template
            variables: Dictionary of variables for substitution (default: {})
            
        Returns:
            str: Rendered prompt with variables substituted
            
        Raises:
            PromptNotFoundError: If the prompt does not exist
            PromptRenderingError: If rendering fails
        """
        variables = variables or {}
        
        # Load template
        template = self._load_template(name)
        
        # Generate cache key
        cache_key = self._generate_cache_key(name, variables)
        
        # Check if already in cache
        if cache_key in self._rendered_cache:
            # Update timestamp
            self._rendered_timestamps[cache_key] = datetime.datetime.now().timestamp()
            return self._rendered_cache[cache_key]
        
        # Render template
        rendered = self._render_template(template, variables)
        
        # Update cache
        self._rendered_cache[cache_key] = rendered
        self._rendered_timestamps[cache_key] = datetime.datetime.now().timestamp()
        
        # Manage cache size
        self._manage_cache()
        
        return rendered
    
    def list_prompts(self) -> List[str]:
        """
        [Method intent]
        List all available prompt templates.
        
        [Design principles]
        - Provide discovery of available prompts
        - Simple interface for prompt exploration
        
        [Implementation details]
        - Returns a list of prompt names from the index
        
        Returns:
            List[str]: List of prompt template names
        """
        return list(self._available_prompts.keys())
    
    def get_required_variables(self, name: str) -> Set[str]:
        """
        [Method intent]
        Get the set of variables required for a specific prompt template.
        
        [Design principles]
        - Enable validation before rendering
        - Help clients prepare necessary variables
        
        [Implementation details]
        - Loads template if not already cached
        - Returns the set of required variable names
        
        Args:
            name: Name of the prompt template
            
        Returns:
            Set[str]: Set of required variable names
            
        Raises:
            PromptNotFoundError: If the prompt does not exist
        """
        # Load template if not already cached
        if name not in self._template_variables:
            self._load_template(name)
            
        return self._template_variables[name].copy()
    
    def get_version(self, name: str) -> str:
        """
        [Method intent]
        Get the version identifier for a prompt template.
        
        [Design principles]
        - Track prompt template versions
        - Enable version-based decisions
        
        [Implementation details]
        - Loads template if not already cached
        - Returns the version hash
        
        Args:
            name: Name of the prompt template
            
        Returns:
            str: Version identifier (hash)
            
        Raises:
            PromptNotFoundError: If the prompt does not exist
        """
        # Load template if not already cached
        if name not in self._versions:
            self._load_template(name)
            
        return self._versions[name]
    
    def reload_prompt(self, name: str) -> None:
        """
        [Method intent]
        Reload a prompt template from disk.
        
        [Design principles]
        - Support for prompt updates at runtime
        - Clear cache for updated prompts
        
        [Implementation details]
        - Removes template from cache
        - Forces reload on next access
        - Updates version tracking
        
        Args:
            name: Name of the prompt template to reload
            
        Raises:
            PromptNotFoundError: If the prompt does not exist
        """
        # Check if prompt exists
        if name not in self._available_prompts:
            raise PromptNotFoundError(f"Prompt template not found: {name}")
        
        # Remove from caches
        if name in self._template_cache:
            del self._template_cache[name]
        if name in self._template_variables:
            del self._template_variables[name]
        if name in self._versions:
            del self._versions[name]
        
        # Clear rendered cache for this prompt
        keys_to_remove = []
        for key in self._rendered_cache.keys():
            if key.startswith(f"{name}:"):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self._rendered_cache:
                del self._rendered_cache[key]
            if key in self._rendered_timestamps:
                del self._rendered_timestamps[key]
        
        # Force reload on next access
        self._load_template(name)
        self._logger.info(f"Reloaded prompt template: {name}")
    
    def reload_all(self) -> None:
        """
        [Method intent]
        Reload all prompt templates from disk.
        
        [Design principles]
        - Support for bulk prompt updates
        - Clear cache for updated prompts
        
        [Implementation details]
        - Rebuilds the prompt index
        - Clears all caches
        - Forces reload on next access
        
        Note: This is a potentially expensive operation and should be used sparingly.
        """
        # Clear all caches
        self._template_cache.clear()
        self._template_variables.clear()
        self._versions.clear()
        self._rendered_cache.clear()
        self._rendered_timestamps.clear()
        
        # Reload index
        self._load_prompt_index()
        self._logger.info("Reloaded all prompt templates")
```

## LangChainPromptAdapter Implementation

Create an adapter for integrating with LangChain prompt templates:

```python
from typing import Dict, Any, Optional, List, Type, Union
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

class LangChainPromptAdapter:
    """
    [Class intent]
    Adapts the PromptManager to work with LangChain prompt templates.
    This enables seamless integration with LangChain components while
    maintaining the benefits of the PromptManager.
    
    [Design principles]
    - Bridge between PromptManager and LangChain
    - Maintain consistent prompt handling
    - Support both text and chat templates
    - Preserve prompt versioning and caching
    
    [Implementation details]
    - Uses PromptManager for underlying prompt management
    - Converts prompts to LangChain format
    - Supports conversion to both text and chat templates
    """
    
    def __init__(self, prompt_manager):
        """
        [Method intent]
        Initialize the adapter with a PromptManager instance.
        
        [Design principles]
        - Composition over inheritance
        - Delegate prompt management to PromptManager
        
        [Implementation details]
        - Stores reference to PromptManager
        
        Args:
            prompt_manager: PromptManager instance
        """
        self.prompt_manager = prompt_manager
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def as_text_template(
        self, 
        name: str, 
        partial_variables: Dict[str, Any] = None
    ) -> PromptTemplate:
        """
        [Method intent]
        Convert a prompt template to a LangChain PromptTemplate.
        
        [Design principles]
        - Support LangChain text template format
        - Allow partial variable binding
        - Maintain prompt versioning
        
        [Implementation details]
        - Gets required variables from PromptManager
        - Creates LangChain PromptTemplate with appropriate parameters
        - Supports partial variables for pre-binding
        
        Args:
            name: Name of the prompt template
            partial_variables: Variables to bind to the template (optional)
            
        Returns:
            PromptTemplate: LangChain prompt template
            
        Raises:
            PromptNotFoundError: If the prompt does not exist
        """
        # Get required variables
        input_variables = self.prompt_manager.get_required_variables(name)
        
        # Handle partial variables
        if partial_variables:
            for var in partial_variables.keys():
                if var in input_variables:
                    input_variables.remove(var)
        
        # Create template function that uses PromptManager
        def get_template():
            # This ensures we always get the latest version of the template
            return self.prompt_manager._load_template(name)
        
        # Create LangChain PromptTemplate
        return PromptTemplate(
            input_variables=list(input_variables),
            partial_variables=partial_variables,
            template_format="f-string",  # We'll use our own rendering
            template=get_template()
        )
    
    def as_chat_template(
        self,
        name: str,
        system_template: bool = False,
        partial_variables: Dict[str, Any] = None
    ) -> ChatPromptTemplate:
        """
        [Method intent]
        Convert a prompt template to a LangChain ChatPromptTemplate.
        
        [Design principles]
        - Support LangChain chat template format
        - Allow specification of message roles
        - Maintain prompt versioning
        
        [Implementation details]
        - Gets required variables from PromptManager
        - Creates LangChain ChatPromptTemplate with appropriate parameters
        - Supports system templates and user templates
        
        Args:
            name: Name of the prompt template
            system_template: Whether this is a system template (default: False)
            partial_variables: Variables to bind to the template (optional)
            
        Returns:
            ChatPromptTemplate: LangChain chat prompt template
            
        Raises:
            PromptNotFoundError: If the prompt does not exist
        """
        # Get required variables
        input_variables = self.prompt_manager.get_required_variables(name)
        
        # Handle partial variables
        if partial_variables:
            for var in partial_variables.keys():
                if var in input_variables:
                    input_variables.remove(var)
        
        # Create template function that uses PromptManager
        def get_template():
            # This ensures we always get the latest version of the template
            return self.prompt_manager._load_template(name)
        
        # Create message based on role
        if system_template:
            messages = [SystemMessage(content=get_template())]
        else:
            messages = [HumanMessage(content=get_template())]
        
        # Create LangChain ChatPromptTemplate
        return ChatPromptTemplate(
            input_variables=list(input_variables),
            partial_variables=partial_variables,
            messages=messages
        )
    
    def format_template(
        self,
        name: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        [Method intent]
        Format a prompt template with variables.
        
        [Design principles]
        - Direct access to prompt rendering
        - Maintain consistent interface with PromptManager
        
        [Implementation details]
        - Delegates to PromptManager
        - Pass-through method for convenience
        
        Args:
            name: Name of the prompt template
            variables: Variables to substitute in the template
            
        Returns:
            str: Formatted prompt
            
        Raises:
            PromptNotFoundError: If the prompt does not exist
            PromptRenderingError: If rendering fails
        """
        return self.prompt_manager.get_prompt(name, variables)
```

## Implementation Steps

1. **Core Prompt Manager**
   - Implement `PromptManager` class in `src/dbp/llm/common/prompt_manager.py`
   - Ensure proper prompt loading from doc/llm/prompts
   - Implement template variable substitution with validation
   - Create caching system with version tracking

2. **LangChain Integration**
   - Create `LangChainPromptAdapter` for LangChain compatibility
   - Implement conversion to text and chat templates
   - Ensure proper handling of input variables

3. **Error Handling and Validation**
   - Implement comprehensive error handling for prompt operations
   - Add validation for required variables
   - Create clear error messages for common failure cases

4. **Utility Methods**
   - Add methods for prompt discovery and inspection
   - Implement cache management utilities
   - Create prompt reload functionality

## Notes

- The PromptManager is designed to work with the existing prompt structure in doc/llm/prompts
- Caching is implemented for both templates and rendered prompts for performance
- Version tracking enables cache invalidation when templates change
- The LangChain adapter provides seamless integration with LangChain components
- All components follow the project's "throw on error" approach

## Next Steps

After completing this phase:
1. Proceed to Phase 5 (Tool Registration System)
2. Implement dynamic tool registry interface
3. Create schema validation for tools
