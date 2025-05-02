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
# Implements the main test command handler which serves as an entry point for
# all testing functionality in the CLI. The test command provides direct access
# to server-side components for testing and debugging purposes.
###############################################################################
# [Source file design principles]
# - Hierarchical command structure with clear delegation
# - Extensible design to accommodate future test subcommands
# - Consistent error handling and user feedback
# - Uses subparsers for clean command-line interface
###############################################################################
# [Source file constraints]
# - Test commands are intended for development and debugging, not production use
# - All subcommands must follow the same handler pattern
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/base.py
# codebase:src/dbp_cli/commands/test/llm.py
###############################################################################
# [GenAI tool change history]
# 2025-05-02T14:16:38Z : Restructured TestCommandHandler to avoid circular imports by CodeAssistant
# * Moved TestCommandHandler directly into __init__.py to avoid circular imports
# 2025-05-02T14:07:26Z : Created package initialization file by CodeAssistant
# * Initial implementation of the test command package
###############################################################################

import argparse
import logging
from typing import Optional

from ..base import BaseCommandHandler
from .llm import LLMTestCommandHandler

logger = logging.getLogger(__name__)

class TestCommandHandler(BaseCommandHandler):
    """
    [Class intent]
    Test subsystems directly using server codebase components.
    This command handler provides a gateway to various test capabilities
    organized into logical subcommands.
    
    [Design principles]
    - Clear subcommand structure for organization of test features
    - Consistent interface following command handler pattern
    - Extensible framework for adding new test functionality
    - Direct access to server components for testing
    
    [Implementation details]
    Implements a parent command that delegates to specialized test
    subcommands based on the test_type parameter. Each subcommand
    is implemented in a dedicated module with its own handler class.
    """
    
    def add_arguments(self, parser):
        """
        [Function intent]
        Add command-line arguments for the test command.
        
        [Design principles]
        - Clear subcommand structure
        - Organized help text
        - Extensible for future test types
        
        [Implementation details]
        - Creates subparsers for different test types
        - Currently supports 'llm' subcommand
        
        Args:
            parser: Command-line argument parser
        """
        subparsers = parser.add_subparsers(dest="test_type", help="Type of test to run")
        
        # Create LLM test subcommand
        llm_parser = subparsers.add_parser("llm", help="Test LLM functionality")
        LLMTestCommandHandler.add_arguments(llm_parser)
        
        # Add more test types here as needed
    
    def execute(self, args):
        """
        [Function intent]
        Execute the appropriate test subcommand based on arguments.
        
        [Design principles]
        - Delegate to appropriate subcommand handler
        - Clear error messaging
        - Consistent return codes
        
        [Implementation details]
        - Checks test_type from args
        - Creates and delegates to appropriate handler
        - Returns handler's exit code
        
        Args:
            args: Command-line arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        if args.test_type == "llm":
            return LLMTestCommandHandler(
                self.mcp_client, 
                self.output, 
                self.progress
            ).execute(args)
        else:
            self.output.error("Please specify a test type")
            return 1
