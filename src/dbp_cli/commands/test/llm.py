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
# Provides command-line interface for testing LLM functionality across different providers.
# This handler serves as a container for provider-specific LLM testing commands, currently
# supporting AWS Bedrock models through the BedrockTestCommandHandler.
###############################################################################
# [Source file design principles]
# - Provider-specific subcommand structure for clear organization
# - Consistent interface across providers for intuitive usage
# - Extensible design to easily add support for additional LLM providers
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with the CLI command hierarchy
# - Must properly initialize and delegate to provider-specific handlers
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/test/bedrock.py
# codebase:src/dbp_cli/commands/base.py
###############################################################################
# [GenAI tool change history]
# 2025-05-06T00:18:38Z : Initial implementation of LLMTestCommandHandler by CodeAssistant
# * Implemented command structure with provider-specific subcommands
# * Added Bedrock provider support
###############################################################################

"""
LLM test command implementation for testing LLM functionalities.
"""

from .bedrock import BedrockTestCommandHandler

class LLMTestCommandHandler:
    """
    [Class intent]
    Provides command-line interface for testing LLM functionality
    using actual LLM implementations from the server codebase.
    
    [Design principles]
    - Provider-specific subcommand structure
    - Consistent interface across providers
    - Extensible for additional LLM providers
    
    [Implementation details]
    - Uses subparsers for different LLM providers
    - Currently supports Bedrock provider
    - Delegates to specialized handlers for each provider
    """
    
    @staticmethod
    def add_arguments(parser):
        """
        [Function intent]
        Add command-line arguments for the LLM test command.
        
        [Design principles]
        - Clear subcommand structure
        - Organized help text
        - Extensible for future LLM providers
        
        [Implementation details]
        - Creates subparsers for different LLM providers
        - Currently supports 'bedrock' subcommand
        
        Args:
            parser: ArgumentParser object to add arguments to
        """
        subparsers = parser.add_subparsers(dest="llm_provider", help="LLM provider to test")
        
        # Create Bedrock test subcommand
        bedrock_parser = subparsers.add_parser("bedrock", help="Test AWS Bedrock models")
        BedrockTestCommandHandler.add_arguments(bedrock_parser)
        
        # Add more LLM providers here as needed
    
    def __init__(self, mcp_client, output_formatter, progress_indicator):
        """
        [Function intent]
        Initialize the LLM test command handler.
        
        [Design principles]
        - Consistent dependency injection
        - Clean initialization
        
        [Implementation details]
        - Stores references to required services
        
        Args:
            mcp_client: MCP client for API access
            output_formatter: Output formatter for displaying results
            progress_indicator: Progress indicator for showing progress
        """
        self.mcp_client = mcp_client
        self.output = output_formatter
        self.progress = progress_indicator
    
    def execute(self, args):
        """
        [Function intent]
        Execute the appropriate LLM provider test based on arguments.
        
        [Design principles]
        - Delegate to appropriate provider handler
        - Clear error messaging
        - Consistent return codes
        
        [Implementation details]
        - Checks llm_provider from args
        - Creates and delegates to appropriate handler
        - Returns handler's exit code
        
        Args:
            args: Command-line arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        if args.llm_provider == "bedrock":
            return BedrockTestCommandHandler(
                self.mcp_client, 
                self.output, 
                self.progress
            ).execute(args)
        else:
            self.output.error("Please specify an LLM provider (bedrock)")
            return 1
