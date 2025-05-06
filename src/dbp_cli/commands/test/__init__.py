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
# Provides command-line interface for testing various system components directly
# using server codebase functionality. This command serves as an entry point for
# running interactive tests against different parts of the system.
###############################################################################
# [Source file design principles]
# - Clear subcommand structure for different test types
# - Extensible design to easily add support for additional test categories
# - Consistent interface with other CLI commands
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with the CLI command hierarchy
# - Must properly initialize and delegate to specialized test handlers
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/base.py
# codebase:src/dbp_cli/commands/test/llm.py
###############################################################################
# [GenAI tool change history]
# 2025-05-06T00:26:13Z : Fixed circular import issue by moving TestCommandHandler into __init__.py by CodeAssistant
# * Resolved circular dependency between test.py and __init__.py
# 2025-05-06T00:19:53Z : Initial implementation of TestCommandHandler by CodeAssistant
# * Implemented command structure with test type subcommands
# * Added LLM test type support
###############################################################################

"""
Test command implementation for running tests against system components.
"""
from ...commands.base import BaseCommandHandler
from .llm import LLMTestCommandHandler

class TestCommandHandler(BaseCommandHandler):
    """
    [Class intent]
    Provides command-line interface for testing system components directly
    using server codebase functionality.
    
    [Design principles]
    - Clear subcommand structure for different test types
    - Extensible for additional test types in the future
    - Consistent interface with other CLI commands
    
    [Implementation details]
    - Extends BaseCommandHandler for CLI integration
    - Uses subparsers for organized command structure
    - Delegates to specialized handlers for each test type
    """
    
    def __init__(self, mcp_client, output_formatter, progress_indicator):
        """
        [Function intent]
        Initialize the test command handler with required dependencies.
        
        [Design principles]
        - Proper initialization of parent class
        - Dependency injection for required services
        
        [Implementation details]
        - Calls parent class constructor with required arguments
        - Stores references to required services for later use
        
        Args:
            mcp_client: MCP client for API access
            output_formatter: Output formatter for displaying results
            progress_indicator: Progress indicator for showing progress
        """
        super().__init__(mcp_client, output_formatter, progress_indicator)
    
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
            parser: ArgumentParser object to add arguments to
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
