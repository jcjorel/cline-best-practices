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
# Extends the core Bedrock model discovery with additional capabilities such as
# cache management, prompt caching detection, and persistence functionality.
# This file inherits from models_core.py to provide a complete feature set while
# maintaining a clear separation of concerns.
###############################################################################
# [Source file design principles]
# - Cache-first approach for performance optimization
# - Clear feature extension through inheritance
# - Capability-based model feature detection
# - Seamless extension of core discovery functionality
# - Persistence support for long-lived discovery results
###############################################################################
# [Source file constraints]
# - Must maintain singleton pattern consistency with core class
# - Must provide backward compatibility for existing code
# - Must ensure thread safety for file operations
# - Must handle file I/O exceptions gracefully
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/discovery/models_core.py
# system:os
# system:json
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-05-07T08:24:00Z : Added TTL and selective cache clearing support by CodeAssistant
# * Added CACHE_TTL_SECONDS constant (7 days)
# * Implemented is_cache_expired method for TTL-based cache validation
# * Added clear_bedrock_models_cache method to selectively clear model data
# * Preserved latency statistics and other cache content in selective clear
# 2025-05-06T23:26:00Z : Created models_capabilities.py as part of models.py file split by CodeAssistant
# * Split from original models.py file
# * Extracted extended capabilities functionality into separate file
# * Implemented inheritance from BedrockModelDiscovery core class
# * Maintained backward compatibility with existing code
###############################################################################

import os
import json
import logging
import time
from typing import Dict, List, Optional, Any

from .models_core import BedrockModelDiscovery


class BedrockModelCapabilities(BedrockModelDiscovery):
    """
    [Class intent]
    Extends BedrockModelDiscovery with additional capabilities like cache management, 
    latency tracking, and model capability detection such as prompt caching support.
    
    [Design principles]
    - Cache-first approach for performance
    - Integrated caching for efficiency
    - Capability-based model feature detection
    - Seamless extension of core discovery functionality
    
    [Implementation details]
    - Adds file-based cache persistence
    - Implements capability detection for features like prompt caching
    - Provides specialized model filtering based on capabilities
    - Extends the singleton pattern for seamless usage
    """
    
    # Define models that support prompt caching
    _PROMPT_CACHING_SUPPORTED_MODELS = [
        "anthropic.claude-3-5-haiku-",  # Claude 3.5 Haiku
        "anthropic.claude-3-7-sonnet-", # Claude 3.7 Sonnet
        "amazon.nova-micro-",           # Nova Micro
        "amazon.nova-lite-",            # Nova Lite
        "amazon.nova-pro-"              # Nova Pro
    ]
    
    # Cache TTL (7 days in seconds)
    CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
    
    @classmethod
    def get_instance(cls, scan_on_init: bool = False):
        """
        [Method intent]
        Override the parent get_instance method to ensure singleton pattern works 
        properly when extending the base class.
        
        [Design principles]
        - Thread-safe singleton access
        - Seamless extension of parent class
        - Consistent interface with parent
        
        [Implementation details]
        - Overrides parent's get_instance to ensure single instance across both classes
        - Ensures proper type returned
        - Maintains thread safety
        
        Args:
            scan_on_init: If True, perform initial region scan when instance is created
            
        Returns:
            BedrockModelCapabilities: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # Create a new instance of the capabilities class
                    cls._instance = cls()
                    # Also update the parent class instance reference for consistency
                    BedrockModelDiscovery._instance = cls._instance
                    
                    # Optionally perform initial scan
                    if scan_on_init:
                        cls._instance.scan_all_regions()
                        
                    # Try to load cache from default location
                    try:
                        cls._instance.load_cache_from_file()
                    except Exception as e:
                        cls._instance.logger.warning(f"Failed to load cache: {str(e)}")
        
        return cls._instance
    
    def load_cache_from_file(self, file_path: Optional[str] = None) -> bool:
        """
        [Method intent]
        Load model and latency data from a JSON file.
        
        [Design principles]
        - Simple file I/O
        - Optional operation
        - Default path handling
        
        [Implementation details]
        - Uses default path if none specified
        - Basic JSON file loading
        - Updates memory cache with loaded data
        
        Args:
            file_path: Optional path to cache file
            
        Returns:
            bool: True if loading succeeded, False otherwise
        """
        path = file_path or os.path.join(os.path.expanduser("~"), ".dbp", "cache", "bedrock_discovery.json")
        
        try:
            if not os.path.exists(path):
                return False
                
            with open(path, "r") as f:
                data = json.load(f)
            
            # Update memory cache with loaded data
            with self._lock:
                if "models" in data:
                    self._memory_cache["models"] = data["models"]
                if "latency" in data:
                    self._memory_cache["latency"] = data["latency"]
                if "last_updated" in data:
                    self._memory_cache["last_updated"] = data["last_updated"]
                
            self.logger.info(f"Loaded model discovery cache from {path}")
            return True
            
        except Exception as e:
            self.logger.warning(f"Error loading cache from {path}: {str(e)}")
            return False

    def save_cache_to_file(self, file_path: Optional[str] = None, force_empty_models: bool = False) -> bool:
        """
        [Method intent]
        Save current model and latency data to a JSON file.
        
        [Design principles]
        - Simple file I/O
        - Optional operation
        - Default path handling
        - Support for forcing empty models cache
        
        [Implementation details]
        - Uses default path if none specified
        - Basic JSON file saving
        - Creates parent directories if needed
        - Option to force empty models in the saved cache
        
        Args:
            file_path: Optional path to cache file
            force_empty_models: If True, save with empty models dict regardless of memory cache
            
        Returns:
            bool: True if saving succeeded, False otherwise
        """
        path = file_path or os.path.join(os.path.expanduser("~"), ".dbp", "cache", "bedrock_discovery.json")
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # Create a copy of the data to save
            with self._lock:
                data = {
                    "models": {} if force_empty_models else self._memory_cache.get("models", {}),
                    "latency": self._memory_cache.get("latency", {}),
                    "last_updated": self._memory_cache.get("last_updated", {})
                }
                
                # Log whether models cache is empty for debugging
                models_empty = not data["models"]
                self.logger.info(f"Saving cache with models_empty={models_empty}")
            
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
                
            self.logger.info(f"Saved model discovery cache to {path}")
            return True
            
        except Exception as e:
            self.logger.warning(f"Error saving cache to {path}: {str(e)}")
            return False
    
    def clear_cache(self) -> None:
        """
        [Method intent]
        Clear all cached model data.
        
        [Design principles]
        - Complete cache clearing
        - Thread safety
        
        [Implementation details]
        - Removes all model mapping from cache
        - Preserves latency data
        - Logs clearing operations
        
        Returns:
            None
        """
        with self._lock:
            if "models" in self._memory_cache:
                del self._memory_cache["models"]
            if "last_updated" in self._memory_cache:
                if "models" in self._memory_cache["last_updated"]:
                    del self._memory_cache["last_updated"]["models"]
        
        self.logger.info("Model discovery cache cleared")
    
    def clear_bedrock_models_cache(self) -> None:
        """
        [Method intent]
        Selectively clear only the AWS Bedrock models definition from cache,
        preserving region latency statistics and other cache content.
        
        [Design principles]
        - Selective cache clearing
        - Preserve performance-related statistics
        - Thread safety
        
        [Implementation details]
        - Removes only model mapping from cache
        - Maintains latency data and other cache content
        - Updates last_updated timestamp to trigger next scan
        - Logs clearing operation
        
        Returns:
            None
        """
        with self._lock:
            if "models" in self._memory_cache:
                del self._memory_cache["models"]
            if "last_updated" in self._memory_cache:
                if "models" in self._memory_cache["last_updated"]:
                    del self._memory_cache["last_updated"]["models"]
        
        self.logger.info("AWS Bedrock models cache cleared, region latency statistics preserved")
    
    def is_cache_expired(self) -> bool:
        """
        [Method intent]
        Check if the model discovery cache has expired based on TTL
        or if the cache is empty.
        
        [Design principles]
        - Simple TTL check
        - Time-based expiration
        - Default TTL period
        - Empty cache detection
        
        [Implementation details]
        - Checks if models cache exists and has content
        - Compares last updated timestamp with current time
        - Uses CACHE_TTL_SECONDS as expiration period
        
        Returns:
            bool: True if cache has expired or is empty, False otherwise
        """
        with self._lock:
            # Check if models cache is empty or doesn't exist
            models_cache = self._memory_cache.get("models", {})
            if not models_cache:
                return True
                
            # Check timestamp
            last_updated = self._memory_cache.get("last_updated", {}).get("models", 0)
            if not last_updated:
                return True
                
            current_time = time.time()
            return (current_time - last_updated) > self.CACHE_TTL_SECONDS
    
    def supports_prompt_caching(self, model_id: str) -> bool:
        """
        [Method intent]
        Check if a specific model supports prompt caching.
        
        [Design principles]
        - Simple capability checking
        - Model ID prefix matching
        - Clear boolean interface
        
        [Implementation details]
        - Checks if model ID starts with any of the supported model prefixes
        - Returns boolean indicating support
        
        Args:
            model_id: The Bedrock model ID to check
            
        Returns:
            bool: True if the model supports prompt caching, False otherwise
        """
        # Check if the model ID starts with any of the supported prefixes
        for prefix in self._PROMPT_CACHING_SUPPORTED_MODELS:
            if model_id.startswith(prefix):
                return True
                
        return False
    
    def get_prompt_caching_models(self) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Get all models that support prompt caching.
        
        [Design principles]
        - Filtering based on model capability
        - Reuse existing model data
        - Provide complete model information
        
        [Implementation details]
        - Gets all available models
        - Filters models that support prompt caching
        - Returns filtered list with full model information
        
        Returns:
            List[Dict[str, Any]]: List of models that support prompt caching
        """
        all_models = self.get_all_models()
        return [
            model for model in all_models 
            if self.supports_prompt_caching(model["modelId"])
        ]
    
    def get_prompt_caching_support_status(self) -> Dict[str, bool]:
        """
        [Method intent]
        Get prompt caching support status for all available models.
        
        [Design principles]
        - Comprehensive capability checking
        - Model ID based lookup
        - Complete mapping
        
        [Implementation details]
        - Gets all available models
        - Checks each model for prompt caching support
        - Returns model ID to support status mapping
        
        Returns:
            Dict[str, bool]: Mapping of model IDs to their prompt caching support status
        """
        all_models = self.get_all_models()
        return {
            model["modelId"]: self.supports_prompt_caching(model["modelId"])
            for model in all_models
        }
        
    def get_model_availability_table(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        [Method intent]
        Generate a comprehensive availability table for project-supported models,
        including region availability and best regions for each model.
        
        [Design principles]
        - Complete model availability reporting
        - Optional model filtering
        - Structured output for various display formats
        
        [Implementation details]
        - Gets all project-supported models or a specific model if requested
        - Checks availability across regions
        - Determines best region for each model
        - Returns structured data suitable for table display
        
        Args:
            model_id: Optional specific model ID to display
            
        Returns:
            Dict with models data and table formatting information
        """
        # Get project-supported models
        project_models = self.project_supported_models
        
        # Filter for specific model if requested
        if model_id:
            if model_id in project_models:
                models_to_display = [model_id]
            else:
                self.logger.warning(f"Model ID {model_id} not found in project-supported models")
                models_to_display = []
        else:
            models_to_display = sorted(project_models)
        
        # Initialize results
        model_data = []
        
        for model_id in models_to_display:
            # Get regions where this model is available (from cache)
            available_regions = self.get_model_regions(model_id)
            
            # Get best region (from cache)
            best_regions = self.get_best_regions_for_model(model_id)
            best_region = best_regions[0] if best_regions else "N/A"
            
            # Format for display
            short_model_id = model_id.split(":")[0]
            
            # Construct entry
            entry = {
                "model_id": model_id,
                "short_model_id": short_model_id,
                "available_regions": available_regions,
                "best_region": best_region
            }
            
            model_data.append(entry)
        
        # Return structured data
        return {
            "models": model_data,
            "columns": ["Model ID", "Available Regions", "Best Region"],
            "timestamp": self._memory_cache.get("last_updated", {}).get("models", "Unknown")
        }
    
    def get_models_with_access_issues(self) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Identify models with access issues (present in regions but not accessible).
        
        [Design principles]
        - Comprehensive access issue reporting
        - Filtering for models with problems
        - Clear issue isolation
        
        [Implementation details]
        - Checks cached model data across regions
        - Identifies regions where models exist but are not accessible
        - Associates inaccessible regions with model IDs
        - Returns only models that have at least one problematic region
        
        Returns:
            List[Dict[str, Any]]: List of models with access issues, including inaccessible regions
        """
        result = []
        
        # Get all project models
        project_models = self.project_supported_models
        
        with self._lock:
            cached_models = self._memory_cache.get("models", {})
            
            # For each model, find regions where it exists but is not accessible
            for model_id in project_models:
                inaccessible_regions = []
                
                # Check each region for this model
                for region, models in cached_models.items():
                    if model_id in models:
                        # If the model exists but is marked as not accessible, add to inaccessible regions
                        if models[model_id].get("accessible") is False:
                            inaccessible_regions.append(region)
                
                # If we found any inaccessible regions, add to result
                if inaccessible_regions:
                    short_model_id = model_id.split(":")[0]
                    result.append({
                        "model_id": model_id,
                        "short_model_id": short_model_id,
                        "inaccessible_regions": sorted(inaccessible_regions)
                    })
        
        return result
    
    def format_availability_table(self, table_data: Dict[str, Any], selected_model: Optional[str] = None) -> str:
        """
        [Method intent]
        Format model availability data as a text table for display with precise column alignment.
        When a specific model is selected, displays detailed availability information for that model.
        
        [Design principles]
        - Clean table formatting with perfect column alignment
        - Condensed region display with consistent truncation
        - Fixed-width columns with proper spacing
        - Visual consistency across all rows
        - Human-readable timestamp display
        - Enhanced display for selected single models
        
        [Implementation details]
        - Formats model data as a fixed-width text table
        - Condenses region list for readability with consistent formatting
        - Adds header and footer lines with proper alignment
        - Ensures text doesn't break column boundaries
        - Converts timestamp to human-readable format
        - Special formatting for displaying a single selected model
        
        Args:
            table_data: Dict containing models data from get_model_availability_table()
            selected_model: Optional model ID for focused display
            
        Returns:
            str: Formatted table as a string with perfectly aligned columns
        """
        import datetime
        
        # Define column widths - adjusted for better display
        model_width = 40
        regions_width = 55  # Increased by 20 characters as requested
        best_region_width = 15
        
        # Calculate total width
        total_width = model_width + regions_width + best_region_width + 8  # +8 for separators and spacing
        
        # Format timestamp to human-readable
        timestamp = table_data.get("timestamp", "Unknown")
        if timestamp != "Unknown":
            try:
                # Convert timestamp to float if it's a string
                if isinstance(timestamp, str):
                    timestamp = float(timestamp)
                
                # Convert to datetime and format
                dt = datetime.datetime.fromtimestamp(timestamp)
                human_readable_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                human_readable_time = str(timestamp)
        else:
            human_readable_time = "Unknown"
        
        # Special case: If we have a selected model and it's in the table data, display detailed information
        if selected_model and table_data["models"] and len(table_data["models"]) == 1:
            model_entry = table_data["models"][0]
            
            # Create a more focused display for a single selected model
            table = []
            table.append(f"\nSelected Model Availability (as of {human_readable_time}):")
            table.append("-" * 80)
            
            # Model information section
            full_model_id = model_entry.get("model_id", "Unknown")
            short_model_id = model_entry.get("short_model_id", "Unknown")
            
            if full_model_id != short_model_id:
                table.append(f"Model ID: {short_model_id} ({full_model_id})")
            else:
                table.append(f"Model ID: {full_model_id}")
            
            # Display all regions without truncation for a single model
            regions = model_entry.get("available_regions", [])
            if regions:
                table.append(f"Available in {len(regions)} regions:")
                for region in sorted(regions):
                    table.append(f"  - {region}")
            else:
                table.append("Available regions: None")
            
            # Best region with clear labeling
            best_region = model_entry.get("best_region", "N/A")
            table.append(f"Recommended region: {best_region}")
            
            # Additional capabilities if available
            if self.supports_prompt_caching(model_entry.get("model_id", "")):
                table.append("Capabilities: Supports prompt caching")
            
            table.append("-" * 80)
            
            return "\n".join(table)
        
        # Original multi-model table display for when no specific model is selected
        # or multiple models are in table_data
        table = []
        table.append(f"\nAvailability Summary (as of {human_readable_time}):")
        separator_line = "-" * total_width
        table.append(separator_line)
        
        # Header row with precise spacing
        header = f"{'Model ID':<{model_width}} | {'Available Regions':<{regions_width}} | {'Best Region':<{best_region_width}}"
        table.append(header)
        
        table.append(separator_line)
        
        # Add rows with consistent formatting
        for entry in table_data["models"]:
            # Format region display (show first 3, then +N more)
            regions = entry["available_regions"]
            
            # Ensure consistent region string formatting
            if len(regions) > 3:
                # Format with exactly 3 regions + more indicator
                regions_str = ", ".join(regions[:3]) + f" +{len(regions)-3} more"
            else:
                regions_str = ", ".join(regions)
            
            # Truncate if still too long for the column
            if len(regions_str) > regions_width - 3:
                regions_str = regions_str[:regions_width - 7] + "..."
            
            # Create row with precise spacing and alignment
            model_id = entry['short_model_id']
            best_region = entry['best_region']
            
            row = f"{model_id:<{model_width}} | {regions_str:<{regions_width}} | {best_region:<{best_region_width}}"
            table.append(row)
        
        # Add footer with matching width
        table.append(separator_line)
        
        # Add model count to footer
        table.append(f"Found {len(table_data['models'])} models")
        
        # Return as a single string
        return "\n".join(table)
