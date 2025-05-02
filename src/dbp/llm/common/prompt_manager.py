###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements prompt management utilities for LLM interactions, providing loading,
# formatting, caching, and versioning of prompt templates. Serves as a centralized
# system for managing prompt templates stored in the doc/llm/prompts/ directory with
# LangChain integration support.
###############################################################################
# [Source file design principles]
# - Centralizes prompt management logic across the application
# - Loads prompt templates exclusively from doc/llm/prompts directory
# - Provides efficient caching for performance optimization
# - Implements version tracking for prompt templates
# - Supports both native string formatting and LangChain templates
# - Follows strict error handling with no fallbacks for missing templates
# - Provides provider-agnostic approach that works with any LLM provider
###############################################################################
# [Source file constraints]
# - All templates must be located in doc/llm/prompts/ directory
# - Templates must include expected output format instructions for the LLM
# - No fallback implementations if templates are missing
# - Templates must be valid markdown or text files
# - Must not contain provider-specific logic or dependencies
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/exceptions.py
# codebase:doc/DESIGN.md
# codebase:doc/design/LLM_COORDINATION.md
# codebase:doc/llm/prompts/README.md
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-02T10:57:00Z : Enhanced for LangChain/LangGraph integration by CodeAssistant
# * Added version tracking and caching system for prompt templates
# * Implemented variable extraction and validation for templates
# * Added LangChainPromptAdapter for LangChain integration
# 2025-05-02T07:13:00Z : Moved to common directory by Cline
# * Relocated from src/dbp/llm/prompt_manager.py to src/dbp/llm/common/prompt_manager.py
# * Updated header to reflect provider-agnostic nature
# 2025-04-16T11:58:00Z : Initial creation of LLMPromptManager class by Cline
# * Created generic prompt manager with strict template loading requirements.
###############################################################################

import os
import re
import logging
import hashlib
from pathlib import Path
import datetime
from typing import Any, Dict, Optional, List, Set, Type, Union

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from .exceptions import PromptError, PromptNotFoundError, PromptRenderingError

logger = logging.getLogger(__name__)

# Constants
PROMPTS_DIR = "doc/llm/prompts"


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
    
    def __init__(
        self, 
        config: Optional[Any] = None, 
        logger_override: Optional[logging.Logger] = None,
        prompts_dir: str = None, 
        cache_size: int = 100
    ):
        """
        [Class method intent]
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
            config: Configuration object (may contain overrides)
            logger_override: Optional logger instance
            prompts_dir: Directory containing prompt templates (default: doc/llm/prompts)
            cache_size: Maximum number of rendered prompts to cache
        """
        self.config = config or {}
        self.logger = logger_override or logger
        
        # Set prompts directory (default if not specified)
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        
        # Check if directory exists
        if not os.path.isdir(self.prompts_dir):
            self.logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            
        # Initialize caching structures
        self.cache_size = cache_size
        self.template_cache = {}  # name -> template content
        self._template_hashes: Dict[str, str] = {}  # name -> content hash
        self._template_variables: Dict[str, Set[str]] = {}  # name -> required variables
        self._rendered_cache: Dict[str, str] = {}  # cache_key -> rendered prompt
        self._rendered_timestamps: Dict[str, float] = {}  # cache_key -> timestamp
        
        # Track loaded prompt versions
        self._versions: Dict[str, str] = {}  # name -> version hash
        
        # Build available prompts index
        self._available_prompts = {}
        self._load_prompt_index()
        
        self.logger.debug("PromptManager initialized.")
    
    def _load_prompt_index(self) -> None:
        """
        [Class method intent]
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
        
        try:
            # Scan prompts directory for markdown files
            for file_path in Path(self.prompts_dir).glob('*.md'):
                prompt_name = file_path.stem  # Filename without extension
                self._available_prompts[prompt_name] = str(file_path)
                
            # Also check for .txt files
            for file_path in Path(self.prompts_dir).glob('*.txt'):
                prompt_name = file_path.stem
                self._available_prompts[prompt_name] = str(file_path)
                
            self.logger.info(f"Found {len(self._available_prompts)} prompt templates")
        except Exception as e:
            self.logger.error(f"Error loading prompt index: {e}")
    
    def _extract_variables(self, template: str) -> Set[str]:
        """
        [Class method intent]
        Extract all variable names from a template.
        
        [Design principles]
        - Support variable identification for validation
        - Simple regex-based extraction
        
        [Implementation details]
        - Uses regex to find all variable placeholders
        - Returns a set of variable names
        
        Args:
            template: Template content with variables
            
        Returns:
            Set[str]: Set of variable names
        """
        return set(re.findall(self.VARIABLE_PATTERN, template))
    
    def _generate_cache_key(self, name: str, variables: Dict[str, Any]) -> str:
        """
        [Class method intent]
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
    
    def _manage_cache(self) -> None:
        """
        [Class method intent]
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
    
    def get_prompt_template(self, template_name: str) -> str:
        """
        [Class method intent]
        Retrieves the content of a prompt template file, caching results for
        efficiency. Strict error handling ensures that missing templates
        raise appropriate exceptions rather than using fallbacks.
        
        [Design principles]
        - Caches templates to optimize repeated use
        - Provides clear error messages for missing templates
        - Supports multiple file extensions (.md, .txt)
        
        [Implementation details]
        - Checks cache before file system
        - Normalizes template names to handle different input formats
        - Validates template content is not empty
        - Computes hash for version tracking
        - Extracts required variables
        
        Args:
            template_name: The name of the template file (with or without extension).
                          Example: "coordinator_general_query_classifier"

        Returns:
            The content of the template as a string.

        Raises:
            PromptNotFoundError: If the template file cannot be found or loaded.
        """
        # Check if template is already cached
        if template_name in self.template_cache:
            return self.template_cache[template_name]
        
        # Check if in available prompts index
        if template_name in self._available_prompts:
            template_path = self._available_prompts[template_name]
        else:
            # Try to normalize template name
            if not (template_name.endswith('.md') or template_name.endswith('.txt')):
                template_name_md = f"{template_name}.md"
                template_name_txt = f"{template_name}.txt"
                
                # Check if normalized name exists in index
                if template_name_md in self._available_prompts:
                    template_path = self._available_prompts[template_name_md]
                    template_name = template_name_md
                elif template_name_txt in self._available_prompts:
                    template_path = self._available_prompts[template_name_txt]
                    template_name = template_name_txt
                else:
                    # Try direct file system check as fallback
                    template_path_md = os.path.join(self.prompts_dir, template_name_md)
                    template_path_txt = os.path.join(self.prompts_dir, template_name_txt)
                    
                    if os.path.exists(template_path_md):
                        template_path = template_path_md
                        template_name = template_name_md
                        # Add to index
                        self._available_prompts[template_name] = template_path
                    elif os.path.exists(template_path_txt):
                        template_path = template_path_txt
                        template_name = template_name_txt
                        # Add to index
                        self._available_prompts[template_name] = template_path
                    else:
                        raise PromptNotFoundError(f"Prompt template not found: {template_name}")
            else:
                # Try direct file system check
                template_path = os.path.join(self.prompts_dir, template_name)
                if not os.path.exists(template_path):
                    raise PromptNotFoundError(f"Prompt template not found: {template_path}")
                # Add to index
                self._available_prompts[template_name] = template_path
                
        try:
            self.logger.debug(f"Loading prompt template: {template_path}")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if not content.strip():
                raise PromptError(f"Prompt template is empty: {template_path}")
            
            # Compute hash for version tracking
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            self._template_hashes[template_name] = content_hash
            self._versions[template_name] = content_hash[:8]  # First 8 chars as version
            
            # Extract required variables
            self._template_variables[template_name] = self._extract_variables(content)
                
            # Cache the template
            self.template_cache[template_name] = content
            
            self.logger.debug(f"Successfully loaded template: {template_name} ({len(content)} chars)")
            return content
            
        except Exception as e:
            if isinstance(e, (PromptNotFoundError, PromptError)):
                # Re-raise our custom exceptions
                raise
            # Wrap other exceptions in our custom exception
            raise PromptError(f"Failed to load prompt template '{template_name}': {str(e)}") from e

    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """
        [Class method intent]
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
    
    def format_prompt(self, template_name: str, **kwargs) -> str:
        """
        [Class method intent]
        Creates a formatted prompt by loading a template and substituting
        the provided variables into the template placeholders.
        
        [Design principles]
        - Simple interface for template formatting
        - Detailed error reporting for missing variables
        - Works with any template format using standard formatting
        
        [Implementation details]
        - Uses Python's string formatting with named placeholders
        - Wraps formatting errors with useful context
        - Logs successful formatting operations
        
        Args:
            template_name: The name of the template file (with or without extension).
            **kwargs: Variables to format into the template.

        Returns:
            The formatted prompt as a string.

        Raises:
            PromptNotFoundError: If the template file cannot be found or loaded.
            PromptRenderingError: If formatting fails due to missing variables.
        """
        # For backwards compatibility, use get_prompt
        return self.get_prompt(template_name, kwargs)
    
    def get_prompt(self, name: str, variables: Dict[str, Any] = None) -> str:
        """
        [Class method intent]
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
        template = self.get_prompt_template(name)
        
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
        [Class method intent]
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
        [Class method intent]
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
            self.get_prompt_template(name)
            
        return self._template_variables[name].copy()
    
    def get_version(self, name: str) -> str:
        """
        [Class method intent]
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
            self.get_prompt_template(name)
            
        return self._versions[name]
    
    def reload_prompt(self, name: str) -> None:
        """
        [Class method intent]
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
        if name in self.template_cache:
            del self.template_cache[name]
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
        self.get_prompt_template(name)
        self.logger.info(f"Reloaded prompt template: {name}")
    
    def reload_all(self) -> None:
        """
        [Class method intent]
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
        self.template_cache.clear()
        self._template_variables.clear()
        self._versions.clear()
        self._rendered_cache.clear()
        self._rendered_timestamps.clear()
        
        # Reload index
        self._load_prompt_index()
        self.logger.info("Reloaded all prompt templates")


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
    
    def __init__(self, prompt_manager: PromptManager):
        """
        [Class method intent]
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
        [Class method intent]
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
            return self.prompt_manager.get_prompt_template(name)
        
        # Create LangChain PromptTemplate
        template_content = get_template()
        return PromptTemplate(
            input_variables=list(input_variables),
            partial_variables=partial_variables,
            template=template_content
        )
    
    def as_chat_template(
        self,
        name: str,
        system_template: bool = False,
        partial_variables: Dict[str, Any] = None
    ) -> ChatPromptTemplate:
        """
        [Class method intent]
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
        
        # Get template content
        template_content = self.prompt_manager.get_prompt_template(name)
        
        # Create message based on role
        if system_template:
            messages = [SystemMessage(content=template_content)]
        else:
            messages = [HumanMessage(content=template_content)]
        
        # Create LangChain ChatPromptTemplate
        return ChatPromptTemplate.from_messages(
            messages=messages,
            partial_variables=partial_variables
        )
    
    def format_template(
        self,
        name: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        [Class method intent]
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


# For backwards compatibility
LLMPromptManager = PromptManager
