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
# Implements the LLM test command handler which provides testing functionality
# for the LLM subsystem. This handler delegates to provider-specific handlers
# for testing different LLM providers like Bedrock.
###############################################################################
# [Source file design principles]
# - Provider-based delegation for extensible testing capabilities
# - Clean command structure with clear help text
# - Consistent error handling and user feedback
###############################################################################
# [Source file constraints]
# - Must not include provider-specific implementation details
# - Should act as a thin delegation layer to provider-specific handlers
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/base.py
# codebase:src/dbp_cli/commands/test/bedrock.py
###############################################################################
# [GenAI tool change history]
# 2025-05-02T14:08:42Z : Initial implementation of LLMTestCommandHandler by CodeAssistant
# * Created command handler for LLM testing with Bedrock provider support
###############################################################################

import argparse
import logging
from typing import Optional

from ..base import BaseCommandHandler
# Direct import now that we've fixed the package structure
from .bedrock import BedrockTestCommandHandler

logger = logging.getLogger(__name__)

class LLMTestCommandHandler:
    """
    [Class intent]
    Test LLM functionality using server codebase components.
    This handler provides testing capabilities for the LLM subsystem
    with support for various providers.
    
    [Design principles]
    - Provider-based subcommand structure for organizational clarity
    - Extensible design for adding new LLM providers
    - Consistent error handling and user experience
    
    [Implementation details]
    Implements a provider-based command structure that delegates to
    specialized provider handlers based on the llm_provider parameter.
    Each provider handler is implemented in a dedicated module.
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
            parser: Command-line argument parser
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
            self.output.error("Please specify an LLM provider")
            return 1
