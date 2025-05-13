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
# This file serves as the entry point when the package is run directly as a module.
# It provides a command-line interface to run the test analyzer on the included
# test file, allowing for quick functionality validation.
###############################################################################
# [Source file design principles]
# - Simple, direct module execution
# - User-friendly command-line interface
# - Clear error handling and feedback
###############################################################################
# [Source file constraints]
# - Should be kept minimal with actual functionality in test_analyzer.py
# - Should provide clear usage instructions
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/hstc_agno/test_analyzer.py
# codebase:src/dbp_cli/commands/hstc_agno/test_file.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T07:20:00Z : Initial implementation by CodeAssistant
# * Created main module entry point
###############################################################################

"""
Entry point for running the HSTC Agno package as a module.

Usage:
    python -m src.dbp_cli.commands.hstc_agno [file_path] [--save-json]

Arguments:
    file_path    Path to the file to analyze (optional, defaults to included test file)

Options:
    --save-json  Save the analysis result as a JSON file
"""

import os
import sys
from pathlib import Path

# Import the test analyzer
from .test_analyzer import run_test


if __name__ == "__main__":
    # Print usage information if --help or -h is provided
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    try:
        # Get the test file path from the command line or use the default
        if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
            test_file_path = sys.argv[1]
        else:
            # Use the included test file
            script_dir = Path(__file__).resolve().parent
            test_file_path = os.path.join(script_dir, "test_file.py")
        
        # Run the test
        result = run_test(test_file_path)
        
        # Optionally save the full JSON result to a file
        if "--save-json" in sys.argv:
            import json
            output_path = os.path.join(Path(test_file_path).parent, "analyzer_result.json")
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Full result saved to {output_path}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
