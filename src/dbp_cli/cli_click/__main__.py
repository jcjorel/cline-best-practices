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
# Provides a proper entry point for executing the CLI as a module with Python's
# -m flag. This file avoids the module import ambiguity warning that happens
# when main.py is directly executed as a module.
###############################################################################
# [Source file design principles]
# - Serves as a clean entry point for module execution
# - Prevents import ambiguity warnings
# - Follows Python's standard module execution pattern
###############################################################################
# [Source file constraints]
# - Must be lightweight with minimal code
# - Should only import main and call the entry point
# - Must maintain consistent exit code handling
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/main.py
# system:sys
###############################################################################
# [GenAI tool change history]
# 2025-05-13T12:35:00Z : Initial implementation by CodeAssistant
# * Created entry point file to fix import ambiguity warning
###############################################################################

import sys
from src.dbp_cli.cli_click.main import main

if __name__ == "__main__":
    sys.exit(main())
