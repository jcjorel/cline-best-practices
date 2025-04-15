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
# Implements the RelationshipsCommandHandler for the 'relationships' CLI command,
# which allows users to analyze relationships between documentation files and
# generate visual diagrams of these relationships.
###############################################################################
# [Source file design principles]
# - Extends the BaseCommandHandler to implement the 'relationships' command.
# - Supports analyzing relationships for specific documents or directories.
# - Provides flexible output options, including Mermaid diagrams.
# - Allows controlling relationship depth for exploration.
# - Supports saving diagrams to files.
###############################################################################
# [Source file constraints]
# - Depends on the MCP server supporting document relationship analysis.
# - Files to analyze must be accessible from the CLI client's file system.
# - Diagram visualization depends on external tools supporting Mermaid.
###############################################################################
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
# - src/dbp_cli/commands/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T13:10:40Z : Initial creation of RelationshipsCommandHandler by CodeAssistant
# * Implemented command handler for analyzing document relationships and generating diagrams.
###############################################################################

import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from .base import BaseCommandHandler
from ..exceptions import CommandError, APIError

logger = logging.getLogger(__name__)

class RelationshipsCommandHandler(BaseCommandHandler):
    """Handles the 'relationships' command for analyzing document relationships."""
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add relationships-specific arguments to the parser."""
        # Document to analyze (optional)
        parser.add_argument(
            "document",
            nargs="?",
            help="Path to document for relationship analysis"
        )
        
        # Directory option (alternative to document)
        parser.add_argument(
            "--directory", 
            "-d",
            help="Directory to analyze relationships in"
        )
        
        # Diagram options
        parser.add_argument(
            "--diagram", 
            action="store_true", 
            help="Generate a Mermaid diagram"
        )
        parser.add_argument(
            "--save-diagram", 
            metavar="FILE", 
            help="Save diagram to file"
        )
        
        # Relationship depth
        parser.add_argument(
            "--depth", 
            type=int, 
            default=1,
            help="Relationship depth (default: 1)"
        )
        
        # Filtering options
        parser.add_argument(
            "--relationship-type",
            help="Filter by relationship type"
        )
        parser.add_argument(
            "--topic",
            help="Filter by topic"
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the relationships command with the provided arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            # Check if we're generating a diagram or analyzing relationships
            if args.diagram or args.save_diagram:
                return self._generate_diagram(args)
            else:
                return self._analyze_relationships(args)
        
        except CommandError as e:
            self.output.error(str(e))
            return 1
        except Exception as e:
            return self.handle_api_error(e)
    
    def _analyze_relationships(self, args: argparse.Namespace) -> int:
        """
        Analyze relationships for a document or directory.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        # Prepare parameters
        params = self._prepare_parameters(args)
        
        # Log the operation
        target = self._get_target_description(args)
        self.output.info(f"Analyzing relationships for {target} (depth: {args.depth})")
        
        # Execute the API call with progress indicator
        result = self.with_progress(
            "Analyzing relationships",
            self.mcp_client.get_doc_relationships,
            **params
        )
        
        # Display results
        self.output.format_output(result)
        
        # Check for empty results
        if not result.get("relationships", []):
            self.output.info("No relationships found.")
        
        return 0
    
    def _generate_diagram(self, args: argparse.Namespace) -> int:
        """
        Generate a diagram for document relationships.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        # Prepare parameters
        params = self._prepare_parameters(args)
        
        # Log the operation
        target = self._get_target_description(args)
        self.output.info(f"Generating relationship diagram for {target} (depth: {args.depth})")
        
        # Execute the API call with progress indicator
        result = self.with_progress(
            "Generating diagram",
            self.mcp_client.get_mermaid_diagram,
            **params
        )
        
        # Check if diagram was generated
        if "diagram" not in result:
            self.output.error("Failed to generate diagram.")
            return 1
        
        # Save to file if requested
        if args.save_diagram:
            try:
                save_path = Path(args.save_diagram).expanduser().resolve()
                
                # Create directory if it doesn't exist
                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write diagram to file
                with open(save_path, "w") as f:
                    f.write("```mermaid\n")
                    f.write(result["diagram"])
                    f.write("\n```\n")
                
                self.output.success(f"Diagram saved to {save_path}")
            
            except Exception as e:
                self.output.error(f"Failed to save diagram: {e}")
                return 1
        
        # Display diagram
        self.output.info("\nMermaid Diagram:")
        self.output.print("```mermaid")
        self.output.print(result["diagram"])
        self.output.print("```")
        
        return 0
    
    def _prepare_parameters(self, args: argparse.Namespace) -> Dict[str, Any]:
        """
        Prepare parameters for the API call based on command arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Dictionary of parameters for the API call
        """
        params = {}
        
        # Handle document path
        if args.document:
            document_path = Path(args.document).expanduser().resolve()
            if not document_path.exists():
                raise CommandError(f"Document does not exist: {args.document}")
            if not document_path.is_file():
                raise CommandError(f"Document path is not a file: {args.document}")
            
            params["document_path"] = str(document_path)
        
        # Handle directory path
        elif args.directory:
            directory_path = Path(args.directory).expanduser().resolve()
            if not directory_path.exists():
                raise CommandError(f"Directory does not exist: {args.directory}")
            if not directory_path.is_dir():
                raise CommandError(f"Path is not a directory: {args.directory}")
            
            params["directory_path"] = str(directory_path)
        
        # Neither document nor directory specified
        else:
            # Default to current working directory
            params["directory_path"] = "."
        
        # Add depth parameter
        params["depth"] = args.depth
        
        # Add filters
        if args.relationship_type:
            params["relationship_type"] = args.relationship_type
        
        if args.topic:
            params["topic"] = args.topic
        
        return params
    
    def _get_target_description(self, args: argparse.Namespace) -> str:
        """
        Get a human-readable description of the analysis target.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Description string
        """
        if args.document:
            return f"document '{args.document}'"
        elif args.directory:
            return f"directory '{args.directory}'"
        else:
            return "current directory"
