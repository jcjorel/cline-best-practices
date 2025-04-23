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
# Provides the entry point for the DBP CLI when run as a Python module.
# This allows the CLI to be run with `python -m dbp_cli` or directly after
# installation with the `dbp` command.
###############################################################################
# [Source file design principles]
# - Simple entry point that delegates to the main function in cli.py.
# - Handles exit code propagation to the operating system.
# - Catches any unexpected top-level exceptions to prevent stack traces in production use.
###############################################################################
# [Source file constraints]
# - Must execute the main CLI function and exit with the appropriate status code.
# - Should be kept minimal as the actual implementation is in cli.py.
###############################################################################
# [Dependencies]
# other:- src/dbp_cli/cli.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T13:17:15Z : Initial creation of __main__.py entry point by CodeAssistant
# * Implemented entry point with main() function call and error handling.
###############################################################################

import sys
import logging

from .cli import main

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)  # Convention for Ctrl+C
    except Exception as e:
        # This should not happen as all exceptions should be caught in main()
        # but we add this as a final safety net
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        print(f"Error: Unhandled exception occurred: {e}", file=sys.stderr)
        sys.exit(1)
