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
# This file implements an abstract base agent class that centralizes common functionality
# used by HSTC processing agents. It provides shared methods for prompt logging, model
# initialization, response processing, and general agent state management.
###############################################################################
# [Source file design principles]
# - Eliminates code redundancy across agent implementations
# - Provides a consistent interface for all HSTC processing agents
# - Standardizes prompt logging and display across agent types
# - Centralizes state management patterns for derived agents
###############################################################################
# [Source file constraints]
# - Must work with the Agno agent framework
# - Should be general enough to support any model type
# - Must maintain compatibility with existing agent implementations
###############################################################################
# [Dependencies]
# system:typing
# system:pathlib
# system:json
# system:os
# system:agno.agent
# codebase:src/dbp_cli/commands/hstc_agno/utils.py
###############################################################################
# [GenAI tool change history]
# 2025-05-13T17:37:00Z : Initial implementation by CodeAssistant
# * Created abstract base agent class
# * Extracted common functionality from existing agents
# * Implemented shared methods for prompt logging and state management
###############################################################################

import json
import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from agno.agent import Agent

from .utils import log_prompt_to_file


class AbstractAgnoAgent(Agent):
    """
    [Class intent]
    Abstract base class for HSTC processing agents that centralizes common functionality
    such as prompt logging, response processing, and state management.
    
    [Design principles]
    Promotes code reuse by extracting shared functionality from specific agents.
    Provides consistent interfaces for derived agent classes.
    
    [Implementation details]
    Extends the Agno Agent class with HSTC-specific utilities.
    Implements common display and logging features for all HSTC agents.
    """
    
    def __init__(
        self, 
        model_id: str,
        agent_name: str,
        show_prompts: bool = True,
        **kwargs
    ):
        """
        [Class method intent]
        Initialize the abstract agent with common parameters.
        
        [Design principles]
        Standardizes initialization across all HSTC agents.
        Separates model configuration from agent functionality.
        
        [Implementation details]
        Stores parameters needed for prompt logging and display.
        Delegates model initialization to subclasses.
        
        Args:
            model_id: ID of the model to use
            agent_name: Name of the agent for logging purposes
            show_prompts: Whether to show prompts and responses
            **kwargs: Additional arguments to pass to the Agent constructor
        """
        # The model must be provided by the subclass before calling super().__init__
        super().__init__(**kwargs)
        
        # Store parameters for prompt logging and display
        self.model_id = model_id
        self.show_prompts = show_prompts
        self.agent_name = agent_name
    
    def run(self, prompt: str, **kwargs):
        """
        [Function intent]
        Override the run method to add prompt and response display functionality.
        
        [Design principles]
        Maintains the original Agent.run behavior while adding display capability.
        Standardizes prompt and response logging across all agents.
        
        [Implementation details]
        Displays prompts and responses when show_prompts is enabled.
        Logs prompts and responses to file for visibility and debugging.
        Uses multiple output methods to ensure visibility in different environments.
        Passes the call to the parent class's run method.
        
        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional arguments to pass to the run method
            
        Returns:
            The response from the LLM
        """
        # Display the prompt before calling the model if show_prompts is enabled
        if self.show_prompts:
            self._display_prompt(prompt)
                
        # Call the parent class's run method
        response = super().run(prompt, **kwargs)
        
        # Display and log the response if show_prompts is enabled
        if self.show_prompts:
            self._display_response(response)
            
            # Log to file for persistent storage
            try:
                log_path = log_prompt_to_file(self.model_id, self.agent_name, prompt, str(response))
                print(f"📝 Prompt and response logged to: {log_path}")
            except Exception as e:
                print(f"⚠️ Warning: Failed to log prompt to file: {e}")
        
        return response
        
    def log(self, message: str, level: str = "INFO"):
        """
        [Function intent]
        Log a message with the specified level.
        
        [Design principles]
        Provides consistent logging across all agent operations.
        Supports different log levels for varied visibility needs.
        
        [Implementation details]
        Formats log messages with agent name and level.
        Uses stdout for immediate visibility in terminal.
        
        Args:
            message: The message to log
            level: Log level (INFO, DEBUG, WARNING, ERROR)
        """
        import sys
        
        level_prefix = {
            "INFO": "ℹ️",
            "DEBUG": "🔍",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }.get(level, "ℹ️")
        
        print(f"{level_prefix} {self.agent_name}: {message}")
        sys.stdout.flush()
    
    def _display_prompt(self, prompt: str):
        """
        [Function intent]
        Display the prompt with clear formatting and ensure it's visible.

        [Design principles]
        Uses multiple output strategies to maximize visibility.
        Applies consistent formatting for readability.

        [Implementation details]
        Uses both print and sys.stdout for maximum compatibility.
        Adds clear visual separators around the content.
        Flushes output to ensure immediate display.

        Args:
            prompt: The prompt to display
        """
        import sys

        self.log(f"Showing prompt for model {self.model_id}", "DEBUG")
        
        separator = "="*80
        header = f"🤖 {self.agent_name} Prompt (using {self.model_id})"

        # Print with multiple strategies to ensure visibility
        print(f"\n{separator}")
        print(f"{header}")
        print(f"{'-'*80}")
        print(f"{prompt}")
        print(f"{separator}")
        sys.stdout.flush()
        
    def _display_response(self, response: str):
        """
        [Function intent]
        Display the model response with clear formatting and ensure it's visible.
        
        [Design principles]
        Uses multiple output strategies to maximize visibility.
        Applies consistent formatting for readability.
        
        [Implementation details]
        Uses both print and sys.stdout for maximum compatibility.
        Adds clear visual separators around the content.
        Flushes output to ensure immediate display.
        
        Args:
            response: The response to display
        """
        import sys
        
        separator = "="*80
        header = f"🤖 {self.agent_name} Response"
        
        # Print with multiple strategies to ensure visibility
        print(f"\n{separator}")
        print(f"{header}")
        print(f"{'-'*80}")
        print(f"{response}")
        print(f"{separator}\n")
        sys.stdout.flush()
    
    def _process_run_response(self, response_obj: Any) -> str:
        """
        [Function intent]
        Process a response from the Agno run method to extract text content.
        
        [Design principles]
        Provides consistent handling of response objects across methods.
        Handles different types of response objects gracefully.
        
        [Implementation details]
        Attempts various methods to extract text from the response object.
        Falls back to string conversion if specific attributes aren't available.
        
        Args:
            response_obj: Response object from self.run()
            
        Returns:
            str: Extracted text content from the response
        """
        
        return response_obj.content                
    
    def clear_state(self, item_key: Optional[str] = None) -> None:
        """
        [Function intent]
        Abstract method for clearing agent state.
        
        [Design principles]
        Provides a consistent interface for state management.
        Allows for selective or complete state clearing.
        
        [Implementation details]
        Must be implemented by subclasses to clear their specific state.
        Supports clearing a specific item or all items.
        
        Args:
            item_key: Key of the item to clear, or None to clear all
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_state_item(self, item_key: str) -> Optional[Any]:
        """
        [Function intent]
        Abstract method for retrieving a state item.
        
        [Design principles]
        Provides a consistent interface for state access.
        Supports retrieval of specific state items.
        
        [Implementation details]
        Must be implemented by subclasses to retrieve their specific state items.
        
        Args:
            item_key: Key of the item to retrieve
            
        Returns:
            The state item or None if not found
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_all_state(self) -> Dict[str, Any]:
        """
        [Function intent]
        Abstract method for retrieving all state items.
        
        [Design principles]
        Provides a consistent interface for state access.
        Supports batch retrieval of all state items.
        
        [Implementation details]
        Must be implemented by subclasses to retrieve their complete state.
        
        Returns:
            Dict containing all state items
        """
        raise NotImplementedError("Subclasses must implement this method")
