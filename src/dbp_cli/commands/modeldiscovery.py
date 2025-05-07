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
# Provides command-line interface for AWS Bedrock model discovery operations,
# including scanning regions for available models and managing the model cache.
###############################################################################
# [Source file design principles]
# - Clear subcommand structure for model discovery operations
# - Simple interface for cache management
# - TTL-based cache refresh
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with the CLI command hierarchy
# - Must preserve region latency data when clearing model cache
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/base.py
# codebase:src/dbp/llm/bedrock/discovery/models_capabilities.py
###############################################################################
# [GenAI tool change history]
# 2025-05-07T08:24:00Z : Initial implementation of ModeldiscoveryCommandHandler by CodeAssistant
# * Implemented command structure with bedrock subcommand
# * Added bedrock reset command to selectively clear Bedrock model cache
# * Added bedrock scan command with TTL check and --force option
###############################################################################

"""
Model discovery command implementation for AWS Bedrock.
"""

from .base import BaseCommandHandler
from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities
import time

class ModeldiscoveryCommandHandler(BaseCommandHandler):
    """Handles model discovery operations such as scanning AWS regions for available Bedrock models.
    
    [Class intent]
    Provides command-line interface for model discovery operations,
    including scanning regions for available models and managing model cache.
    
    [Design principles]
    - Clear subcommand structure
    - Simple cache management operations
    - TTL-based cache refresh
    
    [Implementation details]
    - Uses subparsers for different operations
    - Delegates to BedrockModelCapabilities for model discovery
    """
    
    def add_arguments(self, parser):
        """
        [Function intent]
        Add command-line arguments for the model discovery command.
        
        [Design principles]
        - Clear subcommand structure
        - Organized help text
        
        [Implementation details]
        - Creates subparsers for different operations
        - Supports 'bedrock reset' and 'bedrock scan' operations
        
        Args:
            parser: ArgumentParser object to add arguments to
        """
        subparsers = parser.add_subparsers(dest="discovery_operation", help="Model discovery operation")
        
        # Create bedrock subcommand
        bedrock_parser = subparsers.add_parser("bedrock", help="AWS Bedrock model discovery operations")
        bedrock_subparsers = bedrock_parser.add_subparsers(dest="bedrock_operation", help="Bedrock operation")
        
        # Add bedrock reset subcommand
        reset_parser = bedrock_subparsers.add_parser("reset", help="Reset Bedrock model cache (preserves region latency)")
        
        # Add bedrock scan subcommand
        scan_parser = bedrock_subparsers.add_parser("scan", help="Scan AWS regions for available Bedrock models")
        scan_parser.add_argument(
            "--force",
            action="store_true",
            help="Force scan regardless of cache TTL"
        )
        
        # Add bedrock show subcommand
        show_parser = bedrock_subparsers.add_parser("show", help="Display table of discovered Bedrock models")
    
    def execute(self, args):
        """
        [Function intent]
        Execute the appropriate model discovery operation based on arguments.
        
        [Design principles]
        - Clear operation routing
        - Consistent error handling
        - User-friendly feedback
        
        [Implementation details]
        - Handles bedrock operations (reset and scan)
        - Includes TTL check for scan operation
        
        Args:
            args: Command-line arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        try:
            # Get model discovery instance
            capabilities = BedrockModelCapabilities.get_instance()
            
            # Handle bedrock operations
            if args.discovery_operation == "bedrock":
                if args.bedrock_operation == "reset":
                    # Use the selective clear method to preserve other cache data
                    capabilities.clear_bedrock_models_cache()
                    
                    # Also update the file cache with empty models but preserve latency
                    capabilities.save_cache_to_file(force_empty_models=True)
                    
                    self.output.success("AWS Bedrock model cache has been reset (region latency preserved)")
                    return 0
                elif args.bedrock_operation == "show":
                    # Get model availability table data
                    table_data = capabilities.get_model_availability_table()
                    
                    # Check if there are models in the table
                    if not table_data["models"]:
                        self.output.warning("No models found in cache. Run 'dbp modeldiscovery bedrock scan' to discover models.")
                        return 1
                    
                    # Format the table
                    formatted_table = capabilities.format_availability_table(table_data)
                    
                    # Print the formatted table
                    self.output.print(formatted_table)
                    
                    # Check if models have associated regions
                    has_regions = False
                    for model in table_data["models"]:
                        if model.get("available_regions") and len(model.get("available_regions", [])) > 0:
                            has_regions = True
                            break
                    
                    # If no regions are associated, suggest a manual scan
                    if not has_regions:
                        self.output.info("\nNo regions are associated with models. Run 'dbp modeldiscovery bedrock scan' to discover model availability.")
                    
                    # Check for models with access issues
                    models_with_issues = capabilities.get_models_with_access_issues()
                    if models_with_issues:
                        # Define column widths for the access issues table
                        model_width = 40
                        issues_total_width = 120  # Set a reasonable total width
                        regions_width = issues_total_width - model_width - 5  # 5 for separator and padding
                        
                        # Create header for access issues table
                        self.output.info("\nModels with Access Issues:")
                        separator_line = "-" * issues_total_width
                        self.output.print(separator_line)
                        header = f"{'Model ID':<{model_width}} | {'Unusable regions (model not enabled or IAM permission issues)'}"
                        self.output.print(header)
                        self.output.print(separator_line)
                        
                        # Add rows for each model with access issues
                        for model in models_with_issues:
                            model_id = model['short_model_id']
                            regions = ", ".join(model['inaccessible_regions'])
                            row = f"{model_id:<{model_width}} | {regions}"
                            self.output.print(row)
                        
                        self.output.print(separator_line)
                    
                    # Get and display cache information
                    last_updated = table_data.get("timestamp", "Unknown")
                    
                    # Format the timestamp if it's a number
                    if isinstance(last_updated, (int, float)) and last_updated > 0:
                        from datetime import datetime, timedelta
                        last_scan_date = datetime.fromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')
                        expiration_date = datetime.fromtimestamp(last_updated + capabilities.CACHE_TTL_SECONDS).strftime('%Y-%m-%d %H:%M:%S')
                        self.output.info(f"\nLast scan: {last_scan_date}")
                        self.output.info(f"Cache expires: {expiration_date}")
                    else:
                        self.output.info("\nLast scan: Unknown")
                        self.output.info("Cache status: May be expired")
                    
                    return 0
                    
                elif args.bedrock_operation == "scan":
                    # Check if cache is expired (unless force is specified)
                    force = getattr(args, "force", False)
                    
                    # Check if cache is expired or empty
                    if not force and not capabilities.is_cache_expired():
                        self.output.info("Model cache is still valid. Use --force to scan anyway.")
                        return 0
                        
                    # If we get here, either force is True or cache is expired/empty
                    # We'll scan regardless
                    
                    # Perform scan
                    self.output.info("Scanning AWS regions for available Bedrock models...")
                    
                    # Create progress message with counter
                    progress_message = "Scanning AWS regions (0/0)"
                    self.progress.start(progress_message)
                    
                    # Define progress callback
                    def update_progress(completed, total):
                        nonlocal progress_message
                        progress_message = f"Scanning AWS regions ({completed}/{total})"
                        self.progress.stop()
                        self.progress.start(progress_message)
                    
                    try:
                        result = capabilities.scan_all_regions(
                            force_refresh=True,
                            progress_callback=update_progress
                        )
                    finally:
                        self.progress.stop()
                    
                    # Save cache to file
                    capabilities.save_cache_to_file()
                    
                    # Display results
                    region_count = len(result.get("models", {}))
                    model_count = sum(len(models) for models in result.get("models", {}).values())
                    
                    self.output.success(f"Scan complete: Found {model_count} models across {region_count} regions")
                    self.output.info(f"Cache updated. Next update in 7 days unless forced.")
                    return 0
                else:
                    self.output.error("Please specify a bedrock operation (reset, scan)")
                    return 1
            else:
                self.output.error("Please specify an operation (bedrock)")
                return 1
                
        except Exception as e:
            self.output.error(f"Error in model discovery: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
