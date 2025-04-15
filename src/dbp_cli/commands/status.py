###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
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
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
# - src/dbp_cli/commands/base.py
# - src/dbp_cli/auth.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T13:13:30Z : Initial creation of StatusCommandHandler by CodeAssistant
# * Implemented command handler for checking status of DBP system.
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
    """Handles the 'status' command for checking DBP system status."""
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add status-specific arguments to the parser."""
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
        Execute the status command with the provided arguments.
        
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
        Show system information.
        
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
        Check server connectivity.
        
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
        except APIError as e:
            self.output.error(f"Server API error: {e}")
        except Exception as e:
            self.output.error(f"Error checking server: {e}")
            
        self.output.print()
        return False
    
    def _check_auth(self, verbose: bool = False) -> bool:
        """
        Check authentication status.
        
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
        Show current settings.
        
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
