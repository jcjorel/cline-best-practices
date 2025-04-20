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
# Implements the StatusCommandHandler for the 'status' CLI command, which allows
# users to check the status of the Documentation-Based Programming system,
# including server connectivity, authentication status, and configuration.
###############################################################################
# [Source file design principles]
# - Extends the BaseCommandHandler to implement the 'status' command.
# - Provides options to check server connectivity and authentication.
# - Displays current configuration settings.
# - Returns appropriate exit codes for automation.
###############################################################################
# [Source file constraints]
# - Server status checks depend on network connectivity.
# - Authentication checks may trigger authorization-only API calls.
###############################################################################
# [Dependencies]
# - src/dbp_cli/commands/base.py
# - src/dbp_cli/auth.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T13:13:30Z : Initial creation of StatusCommandHandler by CodeAssistant
# * Implemented command handler for checking status of DBP system.
# 2025-04-15T14:47:00Z : Enhanced server connectivity error handling by CodeAssistant
# * Added detailed troubleshooting suggestions for different connection error types
# * Improved user guidance for resolving server connection issues
###############################################################################

import argparse
import logging
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .base import BaseCommandHandler
from ..exceptions import CommandError, AuthenticationError, ConnectionError, APIError

logger = logging.getLogger(__name__)

class StatusCommandHandler(BaseCommandHandler):
    """
    [Class intent]
    Handles the 'status' command for checking the state of the DBP system, providing
    users with information about server connectivity, authentication status, and 
    current configuration settings.
    
    [Implementation details]
    Implements various status checks including system information display, server 
    connectivity testing, authentication verification, and configuration display.
    Each check can be performed individually or in combination based on command arguments.
    Troubleshooting guidance is provided for common connection and authentication issues.
    
    [Design principles]
    Informative feedback - provides detailed status information in a readable format.
    Progressive disclosure - shows basic information by default, more details with verbose flag.
    Actionable results - includes specific troubleshooting steps for detected issues.
    User empowerment - provides commands that users can run to resolve common problems.
    """
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        [Function intent]
        Add status-specific command line arguments to the argument parser.
        
        [Implementation details]
        Configures the argument parser with options specific to the status command,
        including server connectivity checks, authentication status, and settings display.
        
        [Design principles]
        Single responsibility principle - focuses only on argument configuration.
        Progressive enhancement - provides useful defaults when no arguments are specified.
        
        Args:
            parser: The argparse parser to add arguments to
        """
        parser.add_argument(
            "--check-server", 
            action="store_true", 
            help="Check server connectivity"
        )
        parser.add_argument(
            "--check-auth", 
            action="store_true", 
            help="Check authentication status"
        )
        parser.add_argument(
            "--show-settings", 
            action="store_true", 
            help="Show current settings"
        )
        parser.add_argument(
            "--verbose", 
            "-v", 
            action="store_true", 
            help="Show detailed information"
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        [Function intent]
        Execute the status command with the provided arguments and display results to the user.
        
        [Implementation details]
        Processes the command arguments and performs the requested status checks.
        If no specific checks are requested, performs all checks.
        Shows system information, checks server connectivity, authentication status, 
        and displays current settings based on the provided arguments.
        
        [Design principles]
        Progressive disclosure - shows only the requested information unless no specific
        checks are requested, in which case shows all status information.
        Fail gracefully - tracks overall status and returns appropriate exit code.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        # If no specific checks are requested, show all
        if not any([args.check_server, args.check_auth, args.show_settings]):
            args.check_server = True
            args.check_auth = True
            args.show_settings = True
        
        # Show system information
        self._show_system_info(verbose=args.verbose)
        
        # Track overall status
        status_ok = True
        
        # Check server connectivity if requested
        if args.check_server:
            server_ok = self._check_server(verbose=args.verbose)
            status_ok = status_ok and server_ok
        
        # Check authentication if requested
        if args.check_auth:
            auth_ok = self._check_auth(verbose=args.verbose)
            status_ok = status_ok and auth_ok
        
        # Show settings if requested
        if args.show_settings:
            self._show_settings(verbose=args.verbose)
        
        # Return 0 for success, 1 for any failures
        return 0 if status_ok else 1
    
    def _show_system_info(self, verbose: bool = False) -> None:
        """
        [Function intent]
        Display basic system information to provide context for status checks.
        
        [Implementation details]
        Prints platform information, Python version, current time, and in verbose mode,
        adds working directory, Python executable path, and relevant environment variables.
        Masks sensitive environment variables like API keys.
        
        [Design principles]
        Security-first - masks sensitive information like API keys.
        Progressive disclosure - shows basic information by default, more details in verbose mode.
        
        Args:
            verbose: Whether to show detailed information
        """
        self.output.info("=== System Information ===")
        
        # Basic system information
        self.output.info(f"Platform: {platform.platform()}")
        self.output.info(f"Python: {sys.version.split()[0]}")
        self.output.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show more details if verbose
        if verbose:
            self.output.info(f"Working Directory: {Path.cwd()}")
            self.output.info(f"Python Path: {sys.executable}")
            
            # Show environment variables that might affect the CLI
            import os
            env_vars = {
                k: v for k, v in os.environ.items() 
                if k.startswith(("DBP_", "MCP_", "PYTHONPATH"))
            }
            if env_vars:
                self.output.info("Environment Variables:")
                for k, v in env_vars.items():
                    if k == "DBP_API_KEY":
                        v = "***" # Mask the API key
                    self.output.info(f"  {k}={v}")
        
        self.output.print()
    
    def _check_server(self, verbose: bool = False) -> bool:
        """
        [Function intent]
        Check connectivity to the MCP server and display status information.
        
        [Implementation details]
        Retrieves server URL from configuration, displays it, and attempts to connect.
        On success, shows server version and details if available.
        On failure, provides specific troubleshooting guidance based on the error type.
        Uses the progress indicator during connection attempts.
        
        [Design principles]
        User-focused error handling - provides specific troubleshooting guidance for different errors.
        Helpful feedback - includes server URL and version information when available.
        Status reporting - returns boolean result for status tracking.
        
        Args:
            verbose: Whether to show detailed information
            
        Returns:
            True if server is reachable, False otherwise
        """
        self.output.info("=== Server Status ===")
        
        # Get server URL
        server_url = self.mcp_client.config_manager.get("mcp_server.url")
        
        if not server_url:
            self.output.error("Server URL not configured")
            return False
        
        self.output.info(f"MCP Server URL: {server_url}")
        
        # Check connectivity
        try:
            self.output.info("Checking server connectivity...")
            result = self.with_progress(
                "Connecting to server",
                self.mcp_client.get_server_status
            )
            
            # Display server information
            if "version" in result:
                self.output.success(f"Server is running (version {result['version']})")
            else:
                self.output.success("Server is running")
                
            # Show detailed server information if available and verbose
            if verbose and "details" in result:
                details = result["details"]
                self.output.info("Server Details:")
                
                for key, value in details.items():
                    self.output.info(f"  {key}: {value}")
                    
            self.output.print()
            return True
            
        except ConnectionError as e:
            self.output.error(f"Server connection failed: {e}")
            
            # Extract the error message to provide more specific guidance
            error_str = str(e).lower()
            cause = getattr(e, '__cause__', None)
            cause_str = str(cause).lower() if cause else ""
            
            # Provide specific troubleshooting guidance based on error type
            if "connection refused" in error_str or "connection refused" in cause_str:
                self.output.info("\nTroubleshooting suggestions:")
                self.output.info("1. Check if the MCP server is running at the configured URL")
                self.output.info("2. To start the MCP server, run: dbp server start")
                self.output.info("3. Verify the server port is correct (default: 6231)")
                self.output.info("4. Ensure no firewall is blocking the connection")
                self.output.info("5. Try configuring a different port with:")
                self.output.info("   dbp config set mcp_server.url http://localhost:<port>")
            elif "timed out" in error_str or "timed out" in cause_str:
                self.output.info("\nTroubleshooting suggestions:")
                self.output.info("1. The server might be overloaded or unresponsive")
                self.output.info("2. Try increasing the request timeout:")
                self.output.info("   dbp config set mcp_server.timeout 60")
                self.output.info("3. Check if the MCP server is running")
            elif "name resolution" in error_str or "name resolution" in cause_str:
                self.output.info("\nTroubleshooting suggestions:")
                self.output.info("1. Check your internet connection")
                self.output.info("2. Verify the server hostname is correct")
                self.output.info("3. If using a custom domain, check DNS settings")
            else:
                self.output.info("\nTroubleshooting suggestions:")
                self.output.info("1. Check if the MCP server is running")
                self.output.info("2. Verify the server URL is correct")
                self.output.info("3. Try restarting the MCP server")
                
        except APIError as e:
            self.output.error(f"Server API error: {e}")
            self.output.info("\nTroubleshooting suggestions:")
            self.output.info("1. The server is running but reported an API error")
            self.output.info("2. Check server logs for more information")
            self.output.info("3. Try restarting the MCP server")
            
        except Exception as e:
            self.output.error(f"Error checking server: {e}")
            self.output.info("\nTroubleshooting suggestions:")
            self.output.info("1. Check your network connection")
            self.output.info("2. Verify the server URL configuration")
            self.output.info("3. See application logs for detailed error information")
            
        self.output.print()
        return False
    
    def _check_auth(self, verbose: bool = False) -> bool:
        """
        [Function intent]
        Check authentication status with the MCP server and display results.
        
        [Implementation details]
        Verifies if an API key is configured. If no key is found, displays guidance.
        In verbose mode, tests authentication by making an API call to validate the key.
        Uses the progress indicator during authentication tests.
        
        [Design principles]
        Actionable feedback - provides guidance when authentication is not configured.
        Progressive verification - simple config check by default, actual test in verbose mode.
        Status reporting - returns boolean result for status tracking.
        
        Args:
            verbose: Whether to show detailed information
            
        Returns:
            True if authenticated, False otherwise
        """
        self.output.info("=== Authentication Status ===")
        
        # Check if API key is configured
        api_key_configured = self.mcp_client.auth_manager.is_authenticated()
        
        if not api_key_configured:
            self.output.error("No API key configured")
            self.output.info("To configure an API key, run:")
            self.output.info("  dbp config set mcp_server.api_key YOUR_KEY --save")
            
            self.output.print()
            return False
        
        self.output.success("API key is configured")
        
        # Test authentication by making an API call if verbose
        if verbose:
            try:
                self.output.info("Testing authentication...")
                # We'll use the server status API since it's lightweight
                result = self.with_progress(
                    "Authenticating",
                    self.mcp_client.get_server_status
                )
                
                self.output.success("Authentication successful")
                
            except AuthenticationError as e:
                self.output.error(f"Authentication failed: {e}")
                self.output.print()
                return False
                
            except Exception as e:
                self.output.error(f"Error testing authentication: {e}")
                self.output.print()
                return False
        
        self.output.print()
        return True
    
    def _show_settings(self, verbose: bool = False) -> None:
        """
        [Function intent]
        Display current configuration settings to the user.
        
        [Implementation details]
        Shows important settings like server URL, timeout, API key status, output format,
        and UI preferences. In verbose mode, displays all configuration settings.
        Masks sensitive values like API keys for security.
        
        [Design principles]
        Security-first - masks sensitive configuration values.
        Progressive disclosure - shows key settings by default, all settings in verbose mode.
        Helpful format - organizes settings logically for easy scanning.
        
        Args:
            verbose: Whether to show detailed information
        """
        self.output.info("=== Current Settings ===")
        
        # Get important settings
        settings = {
            "Server URL": self.mcp_client.config_manager.get("mcp_server.url"),
            "Request Timeout": f"{self.mcp_client.config_manager.get('mcp_server.timeout', 30)}s",
            "API Key": "Configured" if self.mcp_client.auth_manager.is_authenticated() else "Not configured",
            "Output Format": self.mcp_client.config_manager.get("cli.output_format", "text"),
            "Color Output": self.mcp_client.config_manager.get("cli.color", True),
            "Progress Indicators": self.mcp_client.config_manager.get("cli.progress_bar", True),
        }
        
        # Display key settings
        for key, value in settings.items():
            self.output.info(f"{key}: {value}")
        
        # Show all settings if verbose
        if verbose:
            self.output.info("\nAll Settings:")
            full_config = self.mcp_client.config_manager.get_config_dict()
            
            def print_nested_dict(data: Dict[str, Any], prefix: str = ""):
                for k, v in data.items():
                    prefixed_key = f"{prefix}.{k}" if prefix else k
                    
                    if isinstance(v, dict):
                        print_nested_dict(v, prefixed_key)
                    else:
                        # Mask sensitive values
                        if "api_key" in prefixed_key.lower() and v is not None:
                            v = "***"
                        self.output.info(f"  {prefixed_key}: {v}")
            
            print_nested_dict(full_config)
        
        self.output.print()
