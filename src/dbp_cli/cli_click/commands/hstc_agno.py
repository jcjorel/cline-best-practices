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
# Integrates the existing hstc_agno Click command group with the main CLI.
# Provides a direct connection between the existing Click command and the new CLI.
###############################################################################
# [Source file design principles]
# - Direct integration with existing Click commands
# - Maintain existing command behavior
# - Ensure consistent context handling
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility with the original command
# - Must ensure proper context passing between commands
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/hstc_agno/cli.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T17:17:19Z : Fixed import error by CodeAssistant
# * Changed relative import to absolute import to fix "ImportError: attempted relative import beyond top-level package"
# 2025-05-12T15:58:06Z : Initial implementation by CodeAssistant
# * Integrated hstc_agno Click command with main CLI
###############################################################################

"""
[Function intent]
Import and expose the existing hstc_agno Click command group for integration with the main CLI.

[Design principles]
Direct integration with no behavior changes ensures compatibility.
Maintain the existing command structure and behavior.

[Implementation details]
Simply import the existing Click command group for use in the main CLI.
No additional wrapping or modification is needed since it's already a Click command.
"""

# Import the existing hstc_agno Click command group
from dbp_cli.commands.hstc_agno.cli import hstc_agno as hstc_agno_group
