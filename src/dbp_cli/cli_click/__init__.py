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
# Package initialization for the Click-based CLI implementation. This package
# provides a new CLI architecture using Click that will eventually replace the
# existing argparse-based implementation.
###############################################################################
# [Source file design principles]
# - Serves as a container for the Click-based CLI components
# - Makes the main entry point accessible for importing
# - Keeps package structure separate from the legacy CLI
# - Enables gradual migration from argparse to Click
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with existing CLI behavior
# - Should not import argparse components to maintain separation
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/main.py
# system:click
###############################################################################
# [GenAI tool change history]
# 2025-05-13T01:14:00Z : Fixed pass_context import by CodeAssistant
# * Removed pass_context import that no longer exists in main.py
# * Updated exports to reflect current implementation
# 2025-05-12T15:31:16Z : Initial creation of Click-based CLI package by CodeAssistant
# * Created package structure for new Click-based CLI implementation
# * Defined package exports for main entry point
###############################################################################

"""
Click-based implementation of the Documentation-Based Programming CLI.
This module provides a modern, composable command-line interface using Click.
"""

from .main import cli as main_cli

__all__ = ['main_cli']
